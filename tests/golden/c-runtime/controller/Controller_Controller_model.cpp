/* Model behaviour for Controller.Controller.
   The generator creates this file once and never rewrites it. */
#include "Controller_Controller_hooks.h"

fmi2Status Controller_Controller_model_initialize(Controller_Controller_Instance* instance) {
  (void)instance;
  /* TODO: initialise derived model state from its parameters and inputs.
     Parameters already hold their start values; a no-op is valid. */
  return fmi2OK;
}

fmi2Status Controller_Controller_model_do_step(
    Controller_Controller_Instance* instance, fmi2Real current_communication_point,
    fmi2Real communication_step_size) {
  (void)instance;
  (void)current_communication_point;
  (void)communication_step_size;
  /* TODO: advance the model by communication_step_size. */
  return fmi2Error;
}

fmi2Status Controller_Controller_model_terminate(Controller_Controller_Instance* instance) {
  (void)instance;
  return fmi2OK;
}

fmi2Status Controller_Controller_model_reset(Controller_Controller_Instance* instance) {
  (void)instance;
  /* TODO: release anything that must not survive a reset.
     user_data itself survives; the runtime restores it. */
  return fmi2OK;
}

fmi2Status Controller_Controller_model_free(Controller_Controller_Instance* instance) {
  (void)instance;
  /* TODO: release user_data and any resource it owns. */
  return fmi2OK;
}
