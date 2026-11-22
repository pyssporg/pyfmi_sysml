/* Model behaviour for Minimal.Scale: y = gain * u.
   Copy this over the generated Minimal_Scale_model.cpp. The generator creates
   that file once and never rewrites it, so it is the implementer's seam. */
#include "Minimal_Scale_hooks.h"

fmi2Status Minimal_Scale_model_initialize(Minimal_Scale_Instance* instance) {
  instance->y.value = instance->gain * instance->u.value;
  return fmi2OK;
}

fmi2Status Minimal_Scale_model_do_step(
    Minimal_Scale_Instance* instance, fmi2Real current_communication_point,
    fmi2Real communication_step_size) {
  (void)current_communication_point;
  (void)communication_step_size;
  instance->y.value = instance->gain * instance->u.value;
  return fmi2OK;
}

fmi2Status Minimal_Scale_model_terminate(Minimal_Scale_Instance* instance) {
  (void)instance;
  return fmi2OK;
}

fmi2Status Minimal_Scale_model_reset(Minimal_Scale_Instance* instance) {
  (void)instance;
  return fmi2OK;
}

fmi2Status Minimal_Scale_model_free(Minimal_Scale_Instance* instance) {
  (void)instance;
  return fmi2OK;
}
