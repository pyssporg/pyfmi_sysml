#ifndef CONTROLLER_CONTROLLER_HOOKS_H
#define CONTROLLER_CONTROLLER_HOOKS_H

#include "Controller_Controller.h"
#include "fmi2/fmi2Functions.h"

/* Model hooks for Controller.Controller. Implemented in Controller_Controller_model.cpp. */

#ifdef __cplusplus
extern "C" {
#endif

fmi2Status Controller_Controller_model_initialize(Controller_Controller_Instance* instance);

fmi2Status Controller_Controller_model_do_step(
    Controller_Controller_Instance* instance, fmi2Real current_communication_point,
    fmi2Real communication_step_size);

fmi2Status Controller_Controller_model_terminate(Controller_Controller_Instance* instance);

/* Called before fmi2Reset clears the instance. The returned status is
   propagated; the user_data pointer survives the reset. */
fmi2Status Controller_Controller_model_reset(Controller_Controller_Instance* instance);

/* Called from fmi2FreeInstance, before the instance is deleted. The
   status is ignored: the FMI interface cannot report a free failure. */
fmi2Status Controller_Controller_model_free(Controller_Controller_Instance* instance);

#ifdef __cplusplus
}
#endif

#endif  /* CONTROLLER_CONTROLLER_HOOKS_H */
