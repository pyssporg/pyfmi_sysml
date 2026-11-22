/* Runtime smoke harness for the generated FMI 2.0 CoSimulation runtime.
 *
 * The test writes ``vr_meta.h`` into the generated output directory and compiles
 * this file twice: once against the generated model, whose hooks are
 * placeholders, and once with ``HARNESS_MODEL_OK`` against a model whose hooks
 * return ``fmi2OK``. Every component variable is exercised through the public
 * FMI API only.
 */

#include <cstdio>
#include <cstring>

#include "fmi2/fmi2Functions.h"
#include "vr_meta.h"

namespace {

int failures = 0;

void logger(fmi2ComponentEnvironment, fmi2String, fmi2Status, fmi2String,
            fmi2String, ...) {}

void check(bool condition, const char* text, int line) {
  if (!condition) {
    std::fprintf(stderr, "FAIL %s:%d: %s\n", __FILE__, line, text);
    ++failures;
  }
}

#define CHECK(condition) check((condition), #condition, __LINE__)

fmi2Status set_by_type(fmi2Component c, fmi2ValueReference vr, int type,
                       const char* text) {
  fmi2Real real_value = 3.5;
  fmi2Integer integer_value = 3;
  fmi2Boolean boolean_value = fmi2True;
  fmi2String string_value = text;
  switch (type) {
    case 0:
      return fmi2SetReal(c, &vr, 1, &real_value);
    case 1:
      return fmi2SetInteger(c, &vr, 1, &integer_value);
    case 2:
      return fmi2SetBoolean(c, &vr, 1, &boolean_value);
    case 3:
      return fmi2SetString(c, &vr, 1, &string_value);
    default:
      return fmi2Error;
  }
}

}  // namespace

int main() {
  fmi2CallbackFunctions callbacks = {logger, nullptr, nullptr, nullptr,
                                     nullptr};

  CHECK(std::strcmp(fmi2GetTypesPlatform(), "default") == 0);
  CHECK(std::strcmp(fmi2GetVersion(), "2.0") == 0);

  fmi2FreeInstance(nullptr);

  fmi2Component wrong_guid = fmi2Instantiate(
      "harness", fmi2CoSimulation, "{00000000-0000-0000-0000-000000000000}",
      "", &callbacks, fmi2False, fmi2True);
  CHECK(wrong_guid == nullptr);

  fmi2Component wrong_type =
      fmi2Instantiate("harness", fmi2ModelExchange, VR_GUID, "", &callbacks,
                      fmi2False, fmi2True);
  CHECK(wrong_type == nullptr);

  fmi2Component c = fmi2Instantiate("harness", fmi2CoSimulation, VR_GUID, "",
                                    &callbacks, fmi2False, fmi2True);
  CHECK(c != nullptr);
  if (c == nullptr) {
    return 1;
  }

  CHECK(fmi2SetDebugLogging(c, fmi2False, 0, nullptr) == fmi2OK);
  CHECK(fmi2SetupExperiment(c, fmi2False, 0.0, 0.25, fmi2False, 0.0) ==
        fmi2OK);
  CHECK(fmi2EnterInitializationMode(c) == fmi2OK);

  for (int index = 0; index < VR_COUNT; ++index) {
    const fmi2ValueReference vr = static_cast<fmi2ValueReference>(index);
    const int type = k_vr_type[index];
    const bool writable = k_vr_writable[index];

    fmi2Real real_value = 0.0;
    fmi2Integer integer_value = 0;
    fmi2Boolean boolean_value = fmi2False;
    fmi2String string_value = nullptr;

    CHECK(fmi2GetReal(c, &vr, 1, &real_value) ==
          (type == 0 ? fmi2OK : fmi2Error));
    CHECK(fmi2GetInteger(c, &vr, 1, &integer_value) ==
          (type == 1 ? fmi2OK : fmi2Error));
    CHECK(fmi2GetBoolean(c, &vr, 1, &boolean_value) ==
          (type == 2 ? fmi2OK : fmi2Error));
    CHECK(fmi2GetString(c, &vr, 1, &string_value) ==
          (type == 3 ? fmi2OK : fmi2Error));

    fmi2Real real_input = 1.5;
    fmi2Integer integer_input = 3;
    fmi2Boolean boolean_input = fmi2True;
    fmi2String string_input = "probe";

    CHECK(fmi2SetReal(c, &vr, 1, &real_input) ==
          (writable && type == 0 ? fmi2OK : fmi2Error));
    CHECK(fmi2SetInteger(c, &vr, 1, &integer_input) ==
          (writable && type == 1 ? fmi2OK : fmi2Error));
    CHECK(fmi2SetBoolean(c, &vr, 1, &boolean_input) ==
          (writable && type == 2 ? fmi2OK : fmi2Error));
    CHECK(fmi2SetString(c, &vr, 1, &string_input) ==
          (writable && type == 3 ? fmi2OK : fmi2Error));

    if (writable && type == 1) {
      CHECK(fmi2GetInteger(c, &vr, 1, &integer_value) == fmi2OK);
      CHECK(integer_value == integer_input);
    }
    if (writable && type == 2) {
      fmi2Boolean false_input = fmi2False;
      CHECK(fmi2GetBoolean(c, &vr, 1, &boolean_value) == fmi2OK);
      CHECK(boolean_value == fmi2True);
      CHECK(fmi2SetBoolean(c, &vr, 1, &false_input) == fmi2OK);
      CHECK(fmi2GetBoolean(c, &vr, 1, &boolean_value) == fmi2OK);
      CHECK(boolean_value == fmi2False);
    }
    if (writable && type == 3) {
      CHECK(fmi2GetString(c, &vr, 1, &string_value) == fmi2OK);
      CHECK(string_value != nullptr &&
            std::strcmp(string_value, "probe") == 0);
    }
  }

  // A batch with an invalid second VR must not write the first one.
  int probe = -1;
  for (int index = 0; index < VR_COUNT; ++index) {
    if (k_vr_writable[index] && k_vr_type[index] == 0) {
      probe = index;
      break;
    }
  }
  if (probe >= 0) {
    fmi2ValueReference refs[2] = {
        static_cast<fmi2ValueReference>(probe),
        static_cast<fmi2ValueReference>(VR_COUNT)};
    fmi2Real values[2] = {7.5, 8.5};
    fmi2Real readback = 0.0;
    CHECK(fmi2SetReal(c, refs, 1, values) == fmi2OK);
    CHECK(fmi2SetReal(c, refs, 2, values) == fmi2Error);
    CHECK(fmi2GetReal(c, refs, 1, &readback) == fmi2OK);
    CHECK(readback == 7.5);
  }

  fmi2EventInfo event_info = {};
  CHECK(fmi2EnterEventMode(c) == fmi2OK);
  CHECK(fmi2NewDiscreteStates(c, &event_info) == fmi2OK);
  CHECK(event_info.newDiscreteStatesNeeded == fmi2False);
  CHECK(event_info.terminateSimulation == fmi2False);
  CHECK(event_info.nominalsOfContinuousStatesChanged == fmi2False);
  CHECK(event_info.valuesOfContinuousStatesChanged == fmi2False);
  CHECK(event_info.nextEventTimeDefined == fmi2False);
  CHECK(fmi2EnterContinuousTimeMode(c) == fmi2OK);
  fmi2Boolean enter_event_mode = fmi2True;
  fmi2Boolean terminate_simulation = fmi2True;
  CHECK(fmi2CompletedIntegratorStep(c, fmi2True, &enter_event_mode,
                                    &terminate_simulation) == fmi2OK);
  CHECK(enter_event_mode == fmi2False);
  CHECK(terminate_simulation == fmi2False);

  fmi2FMUstate state = nullptr;
  CHECK(fmi2GetFMUstate(c, &state) == fmi2Error);
  CHECK(fmi2SetFMUstate(c, state) == fmi2Error);
  CHECK(fmi2FreeFMUstate(c, &state) == fmi2Error);

  fmi2Status status = fmi2Error;
  CHECK(fmi2GetStatus(c, fmi2PendingStatus, &status) == fmi2OK);
  CHECK(status == fmi2OK);

#ifdef HARNESS_MODEL_OK
  CHECK(fmi2ExitInitializationMode(c) == fmi2OK);
  for (int index = 0; index < VR_COUNT; ++index) {
    const fmi2ValueReference vr = static_cast<fmi2ValueReference>(index);
    const fmi2Status set_status =
        set_by_type(c, vr, k_vr_type[index], "after initialization");
    if (k_vr_parameter[index]) {
      CHECK(set_status == fmi2Error);
    } else if (k_vr_writable[index]) {
      CHECK(set_status == fmi2OK);
    } else {
      CHECK(set_status == fmi2Error);
    }
  }

  CHECK(fmi2DoStep(c, 0.25, 0.5, fmi2True) == fmi2OK);
  fmi2Real last_successful_time = -1.0;
  CHECK(fmi2GetRealStatus(c, fmi2LastSuccessfulTime, &last_successful_time) ==
        fmi2OK);
  CHECK(last_successful_time == 0.75);
  CHECK(fmi2GetStatus(c, fmi2DoStepStatus, &status) == fmi2OK);
  CHECK(status == fmi2OK);
  fmi2Boolean terminated = fmi2True;
  CHECK(fmi2GetBooleanStatus(c, fmi2Terminated, &terminated) == fmi2OK);
  CHECK(terminated == fmi2False);
  CHECK(fmi2Terminate(c) == fmi2OK);
  CHECK(fmi2GetBooleanStatus(c, fmi2Terminated, &terminated) == fmi2OK);
  CHECK(terminated == fmi2True);
  CHECK(fmi2Terminate(c) == fmi2OK);
#else
  CHECK(fmi2ExitInitializationMode(c) == fmi2OK);
  CHECK(fmi2DoStep(c, 0.0, 0.0, fmi2True) == fmi2Error);
  CHECK(fmi2DoStep(c, 0.0, 1.0, fmi2True) == fmi2Error);
  CHECK(fmi2GetStatus(c, fmi2DoStepStatus, &status) == fmi2OK);
  CHECK(status == fmi2Error);
  CHECK(fmi2Terminate(c) == fmi2OK);
#endif

  fmi2FreeInstance(c);
  fmi2FreeInstance(nullptr);

  return failures == 0 ? 0 : 1;
}
