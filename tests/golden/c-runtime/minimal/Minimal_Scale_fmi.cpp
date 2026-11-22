/*
 * Generated FMI 2.0 CoSimulation runtime for Minimal.Scale.
 * Do not edit manually; regenerate with `pyfmi c-runtime`.
 * Model behaviour lives in Minimal_Scale_model.cpp.
 */

#include <cstring>
#include <new>
#include <string>

#include "fmi2/fmi2Functions.h"
#include "Minimal_Scale.h"
#include "Minimal_Scale_hooks.h"

struct Minimal_Scale_Handle {
  Minimal_Scale_Instance* model;
  const fmi2CallbackFunctions* callbacks;
  fmi2Boolean logging_on;
  bool initialized;
  bool terminated;
  fmi2Real start_time;
  fmi2Real last_successful_time;
  fmi2Status last_do_step_status;
};

static Minimal_Scale_Handle* Minimal_Scale_handle(fmi2Component c) {
  return static_cast<Minimal_Scale_Handle*>(c);
}

static void Minimal_Scale_log(fmi2Component c, fmi2Status status,
                       const char* message) {
  Minimal_Scale_Handle* h = Minimal_Scale_handle(c);
  if (h == nullptr || !h->logging_on) {
    return;
  }
  if (h->callbacks == nullptr || h->callbacks->logger == nullptr) {
    return;
  }
  h->callbacks->logger(h->callbacks->componentEnvironment, "Scale",
                       status, "", message);
}

static void Minimal_Scale_instantiate_log(
    const fmi2CallbackFunctions* functions, fmi2Boolean logging_on,
    const char* message) {
  if (!logging_on || functions == nullptr ||
      functions->logger == nullptr) {
    return;
  }
  functions->logger(functions->componentEnvironment, "Scale",
                    fmi2Error, "", message);
}

static bool Minimal_Scale_is_parameter_vr(fmi2ValueReference vr) {
  switch (vr) {
    case MINIMAL_SCALE_VR_GAIN:
      return true;
    default:
      return false;
  }
}

static fmi2Status Minimal_Scale_check_batch(
    fmi2Component c, const fmi2ValueReference vr[], size_t nvr,
    Minimal_DataType expected, bool writing) {
  Minimal_Scale_Handle* h = Minimal_Scale_handle(c);
  if (h == nullptr) {
    return fmi2Error;
  }
  if (nvr > 0 && vr == nullptr) {
    Minimal_Scale_log(c, fmi2Error, "value reference array is null");
    return fmi2Error;
  }
  for (size_t i = 0; i < nvr; ++i) {
    if (vr[i] >= Minimal_Scale_VrCount) {
      Minimal_Scale_log(c, fmi2Error, "value reference is out of range");
      return fmi2Error;
    }
    const Minimal_VrMapping& entry = h->model->vr_map[vr[i]];
    if (entry.data == nullptr) {
      Minimal_Scale_log(c, fmi2Error, "value reference has no storage");
      return fmi2Error;
    }
    if (entry.type != expected) {
      Minimal_Scale_log(c, fmi2Error, "value reference has a different type");
      return fmi2Error;
    }
    if (writing && !entry.writable) {
      Minimal_Scale_log(c, fmi2Error, "value reference is not writable");
      return fmi2Error;
    }
    if (writing && Minimal_Scale_is_parameter_vr(vr[i]) && h->initialized) {
      Minimal_Scale_log(c, fmi2Error,
                  "parameter cannot be set after initialization");
      return fmi2Error;
    }
  }
  return fmi2OK;
}

extern "C" {

FMI2_Export const char* fmi2GetTypesPlatform(void) {
  return "default";
}

FMI2_Export const char* fmi2GetVersion(void) {
  return "2.0";
}

FMI2_Export fmi2Status fmi2SetDebugLogging(
    fmi2Component c, fmi2Boolean loggingOn, size_t nCategories,
    const fmi2String categories[]) {
  Minimal_Scale_Handle* h = Minimal_Scale_handle(c);
  if (h == nullptr) {
    return fmi2Error;
  }
  (void)nCategories;
  (void)categories;
  h->logging_on = loggingOn;
  return fmi2OK;
}

FMI2_Export fmi2Component fmi2Instantiate(
    fmi2String instanceName, fmi2Type fmuType, fmi2String fmuGUID,
    fmi2String fmuResourceLocation,
    const fmi2CallbackFunctions* functions, fmi2Boolean visible,
    fmi2Boolean loggingOn) {
  (void)instanceName;
  (void)fmuResourceLocation;
  (void)visible;
  if (fmuType != fmi2CoSimulation) {
    Minimal_Scale_instantiate_log(functions, loggingOn,
        "fmi2Instantiate: only fmi2CoSimulation is supported");
    return nullptr;
  }
  if (fmuGUID == nullptr || std::strcmp(fmuGUID, MINIMAL_SCALE_GUID) != 0) {
    Minimal_Scale_instantiate_log(functions, loggingOn,
        "fmi2Instantiate: GUID does not match");
    return nullptr;
  }
  Minimal_Scale_Instance* model = new (std::nothrow) Minimal_Scale_Instance{};
  if (model == nullptr) {
    Minimal_Scale_instantiate_log(functions, loggingOn,
        "fmi2Instantiate: cannot allocate the model");
    return nullptr;
  }
  Minimal_Scale_initialize_vr_map(model);
  Minimal_Scale_Handle* handle = new (std::nothrow) Minimal_Scale_Handle{};
  if (handle == nullptr) {
    delete model;
    Minimal_Scale_instantiate_log(functions, loggingOn,
        "fmi2Instantiate: cannot allocate the instance");
    return nullptr;
  }
  handle->model = model;
  handle->callbacks = functions;
  handle->logging_on = loggingOn;
  handle->last_do_step_status = fmi2OK;
  return static_cast<fmi2Component>(handle);
}

FMI2_Export void fmi2FreeInstance(fmi2Component c) {
  Minimal_Scale_Handle* h = Minimal_Scale_handle(c);
  if (h == nullptr) {
    return;
  }
  (void)Minimal_Scale_model_free(h->model);
  delete h->model;
  delete h;
}

FMI2_Export fmi2Status fmi2SetupExperiment(
    fmi2Component c, fmi2Boolean toleranceDefined, fmi2Real tolerance,
    fmi2Real startTime, fmi2Boolean stopTimeDefined, fmi2Real stopTime) {
  Minimal_Scale_Handle* h = Minimal_Scale_handle(c);
  if (h == nullptr) {
    return fmi2Error;
  }
  (void)toleranceDefined;
  (void)tolerance;
  (void)stopTimeDefined;
  (void)stopTime;
  h->start_time = startTime;
  h->last_successful_time = startTime;
  return fmi2OK;
}

FMI2_Export fmi2Status fmi2EnterInitializationMode(fmi2Component c) {
  Minimal_Scale_Handle* h = Minimal_Scale_handle(c);
  if (h == nullptr) {
    return fmi2Error;
  }
  return fmi2OK;
}

FMI2_Export fmi2Status fmi2ExitInitializationMode(fmi2Component c) {
  Minimal_Scale_Handle* h = Minimal_Scale_handle(c);
  if (h == nullptr) {
    return fmi2Error;
  }
  h->initialized = false;
  fmi2Status status = Minimal_Scale_model_initialize(h->model);
  if (status == fmi2OK) {
    h->initialized = true;
  } else {
    Minimal_Scale_log(c, status,
                  "fmi2ExitInitializationMode: initialization failed");
  }
  return status;
}

FMI2_Export fmi2Status fmi2Terminate(fmi2Component c) {
  Minimal_Scale_Handle* h = Minimal_Scale_handle(c);
  if (h == nullptr) {
    return fmi2Error;
  }
  if (h->terminated) {
    return fmi2OK;
  }
  h->terminated = true;
  fmi2Status status = Minimal_Scale_model_terminate(h->model);
  if (status != fmi2OK) {
    Minimal_Scale_log(c, status, "fmi2Terminate: model termination failed");
  }
  return status;
}

FMI2_Export fmi2Status fmi2Reset(fmi2Component c) {
  Minimal_Scale_Handle* h = Minimal_Scale_handle(c);
  if (h == nullptr) {
    return fmi2Error;
  }
  fmi2Status status = Minimal_Scale_model_reset(h->model);
  if (status != fmi2OK) {
    Minimal_Scale_log(c, status, "fmi2Reset: model reset failed");
    return status;
  }
  void* user_data = h->model->user_data;
  *h->model = Minimal_Scale_Instance{};
  h->model->user_data = user_data;
  Minimal_Scale_initialize_vr_map(h->model);
  h->initialized = false;
  h->terminated = false;
  h->start_time = 0.0;
  h->last_successful_time = 0.0;
  h->last_do_step_status = fmi2OK;
  return fmi2OK;
}

FMI2_Export fmi2Status fmi2GetReal(
    fmi2Component c, const fmi2ValueReference vr[], size_t nvr,
    fmi2Real value[]) {
  if (nvr > 0 && value == nullptr) {
    Minimal_Scale_log(c, fmi2Error, "fmi2GetReal: value array is null");
    return fmi2Error;
  }
  fmi2Status status = Minimal_Scale_check_batch(c, vr, nvr, MINIMAL_DATA_REAL, false);
  if (status != fmi2OK) {
    return status;
  }
  Minimal_Scale_Handle* h = Minimal_Scale_handle(c);
  for (size_t i = 0; i < nvr; ++i) {
    value[i] = *static_cast<fmi2Real*>(h->model->vr_map[vr[i]].data);
  }
  return fmi2OK;
}

FMI2_Export fmi2Status fmi2GetInteger(
    fmi2Component c, const fmi2ValueReference vr[], size_t nvr,
    fmi2Integer value[]) {
  if (nvr > 0 && value == nullptr) {
    Minimal_Scale_log(c, fmi2Error, "fmi2GetInteger: value array is null");
    return fmi2Error;
  }
  fmi2Status status = Minimal_Scale_check_batch(c, vr, nvr, MINIMAL_DATA_INTEGER, false);
  if (status != fmi2OK) {
    return status;
  }
  Minimal_Scale_Handle* h = Minimal_Scale_handle(c);
  for (size_t i = 0; i < nvr; ++i) {
    value[i] = *static_cast<fmi2Integer*>(
        h->model->vr_map[vr[i]].data);
  }
  return fmi2OK;
}

FMI2_Export fmi2Status fmi2GetBoolean(
    fmi2Component c, const fmi2ValueReference vr[], size_t nvr,
    fmi2Boolean value[]) {
  if (nvr > 0 && value == nullptr) {
    Minimal_Scale_log(c, fmi2Error, "fmi2GetBoolean: value array is null");
    return fmi2Error;
  }
  fmi2Status status = Minimal_Scale_check_batch(c, vr, nvr, MINIMAL_DATA_BOOLEAN, false);
  if (status != fmi2OK) {
    return status;
  }
  Minimal_Scale_Handle* h = Minimal_Scale_handle(c);
  for (size_t i = 0; i < nvr; ++i) {
    value[i] = *static_cast<bool*>(h->model->vr_map[vr[i]].data)
                  ? fmi2True : fmi2False;
  }
  return fmi2OK;
}

FMI2_Export fmi2Status fmi2GetString(
    fmi2Component c, const fmi2ValueReference vr[], size_t nvr,
    fmi2String value[]) {
  if (nvr > 0 && value == nullptr) {
    Minimal_Scale_log(c, fmi2Error, "fmi2GetString: value array is null");
    return fmi2Error;
  }
  fmi2Status status = Minimal_Scale_check_batch(c, vr, nvr, MINIMAL_DATA_STRING, false);
  if (status != fmi2OK) {
    return status;
  }
  Minimal_Scale_Handle* h = Minimal_Scale_handle(c);
  for (size_t i = 0; i < nvr; ++i) {
    value[i] = static_cast<std::string*>(
        h->model->vr_map[vr[i]].data)->c_str();
  }
  return fmi2OK;
}

FMI2_Export fmi2Status fmi2SetReal(
    fmi2Component c, const fmi2ValueReference vr[], size_t nvr,
    const fmi2Real value[]) {
  if (nvr > 0 && value == nullptr) {
    Minimal_Scale_log(c, fmi2Error, "fmi2SetReal: value array is null");
    return fmi2Error;
  }
  fmi2Status status = Minimal_Scale_check_batch(c, vr, nvr, MINIMAL_DATA_REAL, true);
  if (status != fmi2OK) {
    return status;
  }
  Minimal_Scale_Handle* h = Minimal_Scale_handle(c);
  for (size_t i = 0; i < nvr; ++i) {
    *static_cast<fmi2Real*>(h->model->vr_map[vr[i]].data) = value[i];
  }
  return fmi2OK;
}

FMI2_Export fmi2Status fmi2SetInteger(
    fmi2Component c, const fmi2ValueReference vr[], size_t nvr,
    const fmi2Integer value[]) {
  if (nvr > 0 && value == nullptr) {
    Minimal_Scale_log(c, fmi2Error, "fmi2SetInteger: value array is null");
    return fmi2Error;
  }
  fmi2Status status = Minimal_Scale_check_batch(c, vr, nvr, MINIMAL_DATA_INTEGER, true);
  if (status != fmi2OK) {
    return status;
  }
  Minimal_Scale_Handle* h = Minimal_Scale_handle(c);
  for (size_t i = 0; i < nvr; ++i) {
    *static_cast<fmi2Integer*>(h->model->vr_map[vr[i]].data) = value[i];
  }
  return fmi2OK;
}

FMI2_Export fmi2Status fmi2SetBoolean(
    fmi2Component c, const fmi2ValueReference vr[], size_t nvr,
    const fmi2Boolean value[]) {
  if (nvr > 0 && value == nullptr) {
    Minimal_Scale_log(c, fmi2Error, "fmi2SetBoolean: value array is null");
    return fmi2Error;
  }
  fmi2Status status = Minimal_Scale_check_batch(c, vr, nvr, MINIMAL_DATA_BOOLEAN, true);
  if (status != fmi2OK) {
    return status;
  }
  Minimal_Scale_Handle* h = Minimal_Scale_handle(c);
  for (size_t i = 0; i < nvr; ++i) {
    *static_cast<bool*>(h->model->vr_map[vr[i]].data) =
        (value[i] != fmi2False);
  }
  return fmi2OK;
}

FMI2_Export fmi2Status fmi2SetString(
    fmi2Component c, const fmi2ValueReference vr[], size_t nvr,
    const fmi2String value[]) {
  if (nvr > 0 && value == nullptr) {
    Minimal_Scale_log(c, fmi2Error, "fmi2SetString: value array is null");
    return fmi2Error;
  }
  fmi2Status status = Minimal_Scale_check_batch(c, vr, nvr, MINIMAL_DATA_STRING, true);
  if (status != fmi2OK) {
    return status;
  }
  for (size_t i = 0; i < nvr; ++i) {
    if (value[i] == nullptr) {
      Minimal_Scale_log(c, fmi2Error, "fmi2SetString: value is null");
      return fmi2Error;
    }
  }
  Minimal_Scale_Handle* h = Minimal_Scale_handle(c);
  for (size_t i = 0; i < nvr; ++i) {
    *static_cast<std::string*>(h->model->vr_map[vr[i]].data) = value[i];
  }
  return fmi2OK;
}

FMI2_Export fmi2Status fmi2GetFMUstate(
    fmi2Component c, fmi2FMUstate* FMUstate) {
  Minimal_Scale_Handle* h = Minimal_Scale_handle(c);
  if (h == nullptr) {
    return fmi2Error;
  }
  (void)FMUstate;
  Minimal_Scale_log(c, fmi2Error, "fmi2GetFMUstate: not supported");
  return fmi2Error;
}

FMI2_Export fmi2Status fmi2SetFMUstate(
    fmi2Component c, fmi2FMUstate FMUstate) {
  Minimal_Scale_Handle* h = Minimal_Scale_handle(c);
  if (h == nullptr) {
    return fmi2Error;
  }
  (void)FMUstate;
  Minimal_Scale_log(c, fmi2Error, "fmi2SetFMUstate: not supported");
  return fmi2Error;
}

FMI2_Export fmi2Status fmi2FreeFMUstate(
    fmi2Component c, fmi2FMUstate* FMUstate) {
  Minimal_Scale_Handle* h = Minimal_Scale_handle(c);
  if (h == nullptr) {
    return fmi2Error;
  }
  (void)FMUstate;
  Minimal_Scale_log(c, fmi2Error, "fmi2FreeFMUstate: not supported");
  return fmi2Error;
}

FMI2_Export fmi2Status fmi2SerializedFMUstateSize(
    fmi2Component c, fmi2FMUstate FMUstate, size_t* size) {
  Minimal_Scale_Handle* h = Minimal_Scale_handle(c);
  if (h == nullptr) {
    return fmi2Error;
  }
  (void)FMUstate;
  (void)size;
  Minimal_Scale_log(c, fmi2Error, "fmi2SerializedFMUstateSize: not supported");
  return fmi2Error;
}

FMI2_Export fmi2Status fmi2SerializeFMUstate(
    fmi2Component c, fmi2FMUstate FMUstate,
    fmi2Byte serializedState[], size_t size) {
  Minimal_Scale_Handle* h = Minimal_Scale_handle(c);
  if (h == nullptr) {
    return fmi2Error;
  }
  (void)FMUstate;
  (void)serializedState;
  (void)size;
  Minimal_Scale_log(c, fmi2Error, "fmi2SerializeFMUstate: not supported");
  return fmi2Error;
}

FMI2_Export fmi2Status fmi2DeSerializeFMUstate(
    fmi2Component c, const fmi2Byte serializedState[],
    size_t size, fmi2FMUstate* FMUstate) {
  Minimal_Scale_Handle* h = Minimal_Scale_handle(c);
  if (h == nullptr) {
    return fmi2Error;
  }
  (void)serializedState;
  (void)size;
  (void)FMUstate;
  Minimal_Scale_log(c, fmi2Error, "fmi2DeSerializeFMUstate: not supported");
  return fmi2Error;
}

FMI2_Export fmi2Status fmi2GetDirectionalDerivative(
    fmi2Component c, const fmi2ValueReference vUnknown_ref[],
    size_t nUnknown, const fmi2ValueReference vKnown_ref[],
    size_t nKnown, const fmi2Real dvKnown[],
    fmi2Real dvUnknown[]) {
  Minimal_Scale_Handle* h = Minimal_Scale_handle(c);
  if (h == nullptr) {
    return fmi2Error;
  }
  (void)vUnknown_ref;
  (void)nUnknown;
  (void)vKnown_ref;
  (void)nKnown;
  (void)dvKnown;
  (void)dvUnknown;
  Minimal_Scale_log(c, fmi2Error, "fmi2GetDirectionalDerivative: not supported");
  return fmi2Error;
}

FMI2_Export fmi2Status fmi2EnterEventMode(fmi2Component c) {
  Minimal_Scale_Handle* h = Minimal_Scale_handle(c);
  if (h == nullptr) {
    return fmi2Error;
  }
  return fmi2OK;
}

FMI2_Export fmi2Status fmi2NewDiscreteStates(
    fmi2Component c, fmi2EventInfo* fmi2eventInfo) {
  Minimal_Scale_Handle* h = Minimal_Scale_handle(c);
  if (h == nullptr || fmi2eventInfo == nullptr) {
    Minimal_Scale_log(c, fmi2Error, "fmi2NewDiscreteStates: null argument");
    return fmi2Error;
  }
  *fmi2eventInfo = fmi2EventInfo{};
  return fmi2OK;
}

FMI2_Export fmi2Status fmi2EnterContinuousTimeMode(
    fmi2Component c) {
  Minimal_Scale_Handle* h = Minimal_Scale_handle(c);
  if (h == nullptr) {
    return fmi2Error;
  }
  return fmi2OK;
}

FMI2_Export fmi2Status fmi2CompletedIntegratorStep(
    fmi2Component c, fmi2Boolean noSetFMUStatePriorToCurrentPoint,
    fmi2Boolean* enterEventMode, fmi2Boolean* terminateSimulation) {
  Minimal_Scale_Handle* h = Minimal_Scale_handle(c);
  if (h == nullptr || enterEventMode == nullptr ||
      terminateSimulation == nullptr) {
    Minimal_Scale_log(c, fmi2Error,
                  "fmi2CompletedIntegratorStep: null argument");
    return fmi2Error;
  }
  (void)noSetFMUStatePriorToCurrentPoint;
  *enterEventMode = fmi2False;
  *terminateSimulation = fmi2False;
  return fmi2OK;
}

FMI2_Export fmi2Status fmi2SetRealInputDerivatives(
    fmi2Component c, const fmi2ValueReference vr[], size_t nvr,
    const fmi2Integer order[], const fmi2Real value[]) {
  Minimal_Scale_Handle* h = Minimal_Scale_handle(c);
  if (h == nullptr) {
    return fmi2Error;
  }
  (void)vr;
  (void)nvr;
  (void)order;
  (void)value;
  Minimal_Scale_log(c, fmi2Error, "fmi2SetRealInputDerivatives: not supported");
  return fmi2Error;
}

FMI2_Export fmi2Status fmi2GetRealOutputDerivatives(
    fmi2Component c, const fmi2ValueReference vr[], size_t nvr,
    const fmi2Integer order[], fmi2Real value[]) {
  Minimal_Scale_Handle* h = Minimal_Scale_handle(c);
  if (h == nullptr) {
    return fmi2Error;
  }
  (void)vr;
  (void)nvr;
  (void)order;
  (void)value;
  Minimal_Scale_log(c, fmi2Error, "fmi2GetRealOutputDerivatives: not supported");
  return fmi2Error;
}

FMI2_Export fmi2Status fmi2DoStep(
    fmi2Component c, fmi2Real currentCommunicationPoint,
    fmi2Real communicationStepSize,
    fmi2Boolean noSetFMUStatePriorToCurrentPoint) {
  Minimal_Scale_Handle* h = Minimal_Scale_handle(c);
  if (h == nullptr) {
    return fmi2Error;
  }
  (void)noSetFMUStatePriorToCurrentPoint;
  if (communicationStepSize <= 0.0) {
    Minimal_Scale_log(c, fmi2Error, "fmi2DoStep: step size is not positive");
    return fmi2Error;
  }
  fmi2Status status = Minimal_Scale_model_do_step(
      h->model, currentCommunicationPoint, communicationStepSize);
  h->last_do_step_status = status;
  if (status == fmi2OK) {
    h->last_successful_time =
        currentCommunicationPoint + communicationStepSize;
  } else {
    Minimal_Scale_log(c, status, "fmi2DoStep: model step failed");
  }
  return status;
}

FMI2_Export fmi2Status fmi2CancelStep(fmi2Component c) {
  Minimal_Scale_Handle* h = Minimal_Scale_handle(c);
  if (h == nullptr) {
    return fmi2Error;
  }
  return fmi2OK;
}

FMI2_Export fmi2Status fmi2GetStatus(
    fmi2Component c, const fmi2StatusKind s, fmi2Status* value) {
  Minimal_Scale_Handle* h = Minimal_Scale_handle(c);
  if (h == nullptr || value == nullptr) {
    Minimal_Scale_log(c, fmi2Error, "fmi2GetStatus: null argument");
    return fmi2Error;
  }
  if (s == fmi2DoStepStatus) {
    *value = h->last_do_step_status;
  } else if (s == fmi2PendingStatus) {
    *value = fmi2OK;  /* no asynchronous step is pending */
  } else {
    Minimal_Scale_log(c, fmi2Error, "fmi2GetStatus: unsupported status kind");
    return fmi2Error;
  }
  return fmi2OK;
}

FMI2_Export fmi2Status fmi2GetRealStatus(
    fmi2Component c, const fmi2StatusKind s, fmi2Real* value) {
  Minimal_Scale_Handle* h = Minimal_Scale_handle(c);
  if (h == nullptr || value == nullptr) {
    Minimal_Scale_log(c, fmi2Error, "fmi2GetRealStatus: null argument");
    return fmi2Error;
  }
  if (s != fmi2LastSuccessfulTime) {
    Minimal_Scale_log(c, fmi2Error,
                  "fmi2GetRealStatus: unsupported status kind");
    return fmi2Error;
  }
  *value = h->last_successful_time;
  return fmi2OK;
}

FMI2_Export fmi2Status fmi2GetIntegerStatus(
    fmi2Component c, const fmi2StatusKind s, fmi2Integer* value) {
  Minimal_Scale_Handle* h = Minimal_Scale_handle(c);
  if (h == nullptr || value == nullptr) {
    Minimal_Scale_log(c, fmi2Error, "fmi2GetIntegerStatus: null argument");
    return fmi2Error;
  }
  (void)s;
  Minimal_Scale_log(c, fmi2Error, "fmi2GetIntegerStatus: unsupported");
  return fmi2Error;
}

FMI2_Export fmi2Status fmi2GetBooleanStatus(
    fmi2Component c, const fmi2StatusKind s, fmi2Boolean* value) {
  Minimal_Scale_Handle* h = Minimal_Scale_handle(c);
  if (h == nullptr || value == nullptr) {
    Minimal_Scale_log(c, fmi2Error, "fmi2GetBooleanStatus: null argument");
    return fmi2Error;
  }
  if (s != fmi2Terminated) {
    Minimal_Scale_log(c, fmi2Error,
                  "fmi2GetBooleanStatus: unsupported status kind");
    return fmi2Error;
  }
  *value = h->terminated ? fmi2True : fmi2False;
  return fmi2OK;
}

FMI2_Export fmi2Status fmi2GetStringStatus(
    fmi2Component c, const fmi2StatusKind s, fmi2String* value) {
  Minimal_Scale_Handle* h = Minimal_Scale_handle(c);
  if (h == nullptr || value == nullptr) {
    Minimal_Scale_log(c, fmi2Error, "fmi2GetStringStatus: null argument");
    return fmi2Error;
  }
  (void)s;
  Minimal_Scale_log(c, fmi2Error, "fmi2GetStringStatus: unsupported");
  return fmi2Error;
}

}
