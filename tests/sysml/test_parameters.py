"""Deployment parameters configure one build per instance, not per process.

Two components of the same generated FMU run in one process, each bound to a
different UDP port through its own FMI parameter values.  A separate run proves
that an unknown transport value fails initialization with ``fmi2Error``.
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
import textwrap
import time
import xml.etree.ElementTree as ET

import pytest
from conftest import compile_runner, free_udp_port, skip_reason
from pyssp_sysml_definitions import core_definitions

from pyfmi_interop import wire
from pyfmi_interop.builder import build_model
from pyfmi_interop.codegen import generate_model
from pyfmi_interop.core import BuildConfig
from pyfmi_interop.ir import model_from_dict
from pyfmi_interop.serialization import packed

pytestmark = [pytest.mark.cpp, pytest.mark.system, pytest.mark.sysml]

_FIXTURE = textwrap.dedent(
    """\
    package ParameterExchange {
      private import ScalarValues::*;
      private import PysspCore::*;

      port def Deployment :> ParameterInterface {
        attribute transport : String = "loopback";
        attribute bind_address : String = "127.0.0.1:0";
        attribute peer_address : String = "";
        attribute queue_depth : Integer = 8;
      }

      port def Command {
        attribute demand : Real;
      }

      port def Status {
        attribute actual : Real;
      }

      part def Exchange {
        in port command : Command;
        out port status : Status;
        in port parameters : Deployment;
      }

      part def Root {
        part exchange : Exchange;
      }
    }
    """
)

_RUNNER = textwrap.dedent(
    r"""
    #include "fmi2Functions.h"

    #include <chrono>
    #include <cstdarg>
    #include <cstdio>
    #include <cstdlib>
    #include <fstream>
    #include <string>
    #include <thread>

    namespace {

    std::string g_log;

    void logger(fmi2ComponentEnvironment, fmi2String, fmi2Status,
                fmi2String, fmi2String message, ...) {
        char buffer[512] = {0};
        va_list args;
        va_start(args, message);
        std::vsnprintf(buffer, sizeof(buffer), message != nullptr ? message : "",
                       args);
        va_end(args);
        g_log += buffer;
        g_log += "\n";
    }

    [[noreturn]] void fail(const char* what) {
        std::fprintf(stderr, "runner error: %s\n", what);
        std::exit(2);
    }

    void expect(fmi2Status status, const char* what) {
        if (status != fmi2OK && status != fmi2Warning) {
            fail(what);
        }
    }

    void* allocate_memory(std::size_t count, std::size_t size) {
        return std::malloc(count * size);
    }

    void free_memory(void* pointer) { std::free(pointer); }

    bool exists(const std::string& path) {
        std::ifstream stream(path);
        return stream.good();
    }

    void wait_for(const std::string& path) {
        for (int attempt = 0; attempt < 4000; ++attempt) {
            if (exists(path)) {
                return;
            }
            std::this_thread::sleep_for(std::chrono::milliseconds(5));
        }
        fail("timed out waiting for a marker file");
    }

    fmi2Component instantiate(const fmi2CallbackFunctions& callbacks,
                              const char* name, const char* guid) {
        fmi2Component component = fmi2Instantiate(
            name, fmi2CoSimulation, guid, "file:///tmp", &callbacks,
            fmi2False, fmi2True);
        if (component == nullptr) {
            fail("fmi2Instantiate failed");
        }
        return component;
    }

    }  // namespace

    int main(int argc, char** argv) {
        fmi2ValueReference transport_vr = 0;
        fmi2ValueReference bind_vr = 0;
        fmi2ValueReference peer_vr = 0;
        fmi2ValueReference output_vr = 0;
        std::string bind_a;
        std::string bind_b;
        std::string ready_file;
        std::string go_file;
        std::string guid = fmi2TypesPlatform;
        bool bad_transport = false;

        for (int index = 1; index < argc; ++index) {
            const std::string arg = argv[index];
            auto next = [&](const char* name) -> const char* {
                if (index + 1 >= argc) {
                    fail(name);
                }
                return argv[++index];
            };
            if (arg == "--transport-vr") {
                transport_vr = static_cast<fmi2ValueReference>(
                    std::strtoul(next("--transport-vr"), nullptr, 10));
            } else if (arg == "--bind-vr") {
                bind_vr = static_cast<fmi2ValueReference>(
                    std::strtoul(next("--bind-vr"), nullptr, 10));
            } else if (arg == "--peer-vr") {
                peer_vr = static_cast<fmi2ValueReference>(
                    std::strtoul(next("--peer-vr"), nullptr, 10));
            } else if (arg == "--output-vr") {
                output_vr = static_cast<fmi2ValueReference>(
                    std::strtoul(next("--output-vr"), nullptr, 10));
            } else if (arg == "--bind-a") {
                bind_a = next("--bind-a");
            } else if (arg == "--bind-b") {
                bind_b = next("--bind-b");
            } else if (arg == "--guid") {
                guid = next("--guid");
            } else if (arg == "--ready-file") {
                ready_file = next("--ready-file");
            } else if (arg == "--go-file") {
                go_file = next("--go-file");
            } else if (arg == "--bad-transport") {
                bad_transport = true;
            } else {
                fail("unknown argument");
            }
        }

        fmi2CallbackFunctions callbacks{};
        callbacks.logger = logger;
        callbacks.allocateMemory = allocate_memory;
        callbacks.freeMemory = free_memory;
        callbacks.stepFinished = nullptr;

        fmi2Component component = instantiate(callbacks, "parameter-runner", guid.c_str());

        if (bad_transport) {
            fmi2ValueReference vr = transport_vr;
            const char* value = "carrier-pigeon";
            expect(fmi2SetString(component, &vr, 1, &value), "set transport");
            expect(fmi2SetupExperiment(component, fmi2False, 0.0, 0.0, fmi2False, 0.0),
                   "setup experiment");
            fmi2Status status = fmi2EnterInitializationMode(component);
            if (status == fmi2OK) {
                // The psysml2 FMI layer has no EnterInitializationMode hook;
                // it reports the transport failure from ExitInitializationMode.
                status = fmi2ExitInitializationMode(component);
            }
            std::printf("enter %d\n", static_cast<int>(status));
            std::printf("log %s\n", g_log.c_str());
            fmi2FreeInstance(component);
            return status == fmi2Error ? 0 : 1;
        }

        fmi2Component second = instantiate(callbacks, "parameter-runner-2", guid.c_str());
        auto configure = [&](fmi2Component target, const std::string& bind) {
            fmi2ValueReference vr = transport_vr;
            const char* transport = "udp";
            expect(fmi2SetString(target, &vr, 1, &transport), "set transport");
            vr = bind_vr;
            const char* address = bind.c_str();
            expect(fmi2SetString(target, &vr, 1, &address), "set bind address");
            vr = peer_vr;
            const char* peer = "";
            expect(fmi2SetString(target, &vr, 1, &peer), "set peer");
            expect(fmi2SetupExperiment(target, fmi2False, 0.0, 0.0, fmi2False, 0.0),
                   "setup experiment");
            expect(fmi2EnterInitializationMode(target), "enter initialization");
            expect(fmi2ExitInitializationMode(target), "exit initialization");
        };

        configure(component, bind_a);
        configure(second, bind_b);

        // Fixed parameters can no longer be written after initialization.
        fmi2ValueReference transport = transport_vr;
        const char* loopback = "loopback";
        if (fmi2SetString(component, &transport, 1, &loopback) == fmi2OK) {
            fail("a parameter write after initialization must fail");
        }
        std::printf("parameter write rejected\n");

        std::ofstream(ready_file) << "ready\n";
        wait_for(go_file);

        double time_s = 0.0;
        for (int step = 0; step < 50; ++step) {
            expect(fmi2DoStep(component, time_s, 0.001, fmi2True), "doStep a");
            expect(fmi2DoStep(second, time_s, 0.001, fmi2True), "doStep b");
            time_s += 0.001;
        }

        fmi2ValueReference vr = output_vr;
        fmi2Real first_value = 0.0;
        fmi2Real second_value = 0.0;
        expect(fmi2GetReal(component, &vr, 1, &first_value), "get a");
        expect(fmi2GetReal(second, &vr, 1, &second_value), "get b");
        std::printf("A %.17g\n", first_value);
        std::printf("B %.17g\n", second_value);

        fmi2Terminate(component);
        fmi2FreeInstance(component);
        fmi2Terminate(second);
        fmi2FreeInstance(second);
        return 0;
    }
    """
)


_SKIP = skip_reason("the two-instance runner is POSIX-only")


@pytest.fixture(scope="module", params=["interop", "psysml2"])
def generated(request, tmp_path_factory):
    pytest.importorskip("pycps_sysml")
    pytest.importorskip("pyfmi_interfaces")
    import pyfmi_sysml as sysml

    layer = request.param
    root = tmp_path_factory.mktemp(f"parameters_{layer}")
    source = root / "parameter_exchange.sysml"
    source.write_text(_FIXTURE, encoding="utf-8")
    config = BuildConfig(serialization="packed", role="adapter")
    if layer == "psysml2":
        parsed = sysml.parse(
            source, includes=[core_definitions()], name="ParameterExchange"
        )
        model_dir = sysml.generate_adapter(parsed, root / "model", config)
    else:
        model = sysml.load_model(source, name="ParameterExchange")
        model_dir = generate_model(model, root / "model", config)
    library = build_model(model_dir, root / "build")
    runner = compile_runner(root, library, _RUNNER, stem="parameter_runner")

    if layer == "psysml2":
        from pyfmi_interop.core import (
            load_adapter_model,
            wire_model_from_adapter_json,
        )

        document = load_adapter_model(model_dir)
        effective = wire_model_from_adapter_json(document)
        by_name = {signal["name"]: signal for signal in document["signals"]}
    else:
        document = json.loads((model_dir / "model.json").read_text(encoding="utf-8"))
        effective = model_from_dict(document)
        by_name = {signal["name"]: signal for signal in document["signals"]}
    guid = "fmi2TypesPlatform"
    if layer == "psysml2":
        description = next(model_dir.glob("*/modelDescription.xml"))
        guid = ET.parse(description).getroot().attrib["guid"]
    return {
        "layer": layer,
        "runner": runner,
        "model": effective,
        "guid": guid,
        "vrs": {name: item["value_reference"] for name, item in by_name.items()},
    }


def _frame(model, value: float) -> bytes:
    payload = packed.encode(model, {"status.actual": value})
    return wire.encode(
        model,
        payload,
        instance=1,
        sequence=1,
        timestamp_ns=0,
        payload_format=wire.PayloadFormat.PACKED,
    )


@pytest.mark.skipif(_SKIP is not None, reason=_SKIP or "")
def test_two_instances_bind_different_udp_ports(generated, tmp_path):
    runner = generated["runner"]
    model = generated["model"]
    vrs = generated["vrs"]
    port_a = free_udp_port()
    port_b = free_udp_port()
    ready = tmp_path / "ready"
    go = tmp_path / "go"

    process = subprocess.Popen(
        [
            str(runner),
            "--guid",
            generated["guid"],
            "--transport-vr",
            str(vrs["transport"]),
            "--bind-vr",
            str(vrs["bind_address"]),
            "--peer-vr",
            str(vrs["peer_address"]),
            "--output-vr",
            str(vrs["status.actual"]),
            "--bind-a",
            f"127.0.0.1:{port_a}",
            "--bind-b",
            f"127.0.0.1:{port_b}",
            "--ready-file",
            str(ready),
            "--go-file",
            str(go),
        ],
        env={
            key: value
            for key, value in os.environ.items()
            if key not in {"PYFMI_INTEROP_TRANSPORT", "PYFMI_INTEROP_TRANSPORT_ENDPOINT"}
        },
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    try:
        deadline = time.monotonic() + 30.0
        while time.monotonic() < deadline and not ready.exists():
            if process.poll() is not None:
                out, err = process.communicate()
                raise AssertionError(f"runner exited early:\n{out}\n{err}")
            time.sleep(0.005)
        assert ready.exists(), "the runner never bound its transports"

        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sender:
            sender.sendto(_frame(model, 11.5), ("127.0.0.1", port_a))
            sender.sendto(_frame(model, 22.5), ("127.0.0.1", port_b))
        time.sleep(0.05)
        go.write_text("go\n", encoding="utf-8")

        out, err = process.communicate(timeout=30)
    finally:
        if process.poll() is None:
            process.kill()
            process.communicate()

    assert process.returncode == 0, out + err
    assert "parameter write rejected" in out
    values = {
        line.split()[0]: float(line.split()[1])
        for line in out.splitlines()
        if line.startswith(("A ", "B "))
    }
    assert values["A"] == 11.5, (out, err)
    assert values["B"] == 22.5, (out, err)


@pytest.mark.skipif(_SKIP is not None, reason=_SKIP or "")
def test_unknown_transport_parameter_fails_initialization(generated, tmp_path):
    runner = generated["runner"]
    vrs = generated["vrs"]

    completed = subprocess.run(
        [
            str(runner),
            "--guid",
            generated["guid"],
            "--transport-vr",
            str(vrs["transport"]),
            "--bind-vr",
            str(vrs["bind_address"]),
            "--peer-vr",
            str(vrs["peer_address"]),
            "--bad-transport",
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )

    combined = completed.stdout + completed.stderr
    assert completed.returncode == 0, combined
    assert "enter 3" in completed.stdout  # fmi2Error
    assert "transport" in combined
    assert "loopback, udp, tcp" in combined
