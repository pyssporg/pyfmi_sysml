// An actuator link with an inbound command port and an outbound feedback port.
// The fixed-length array fields become one scalar FMI variable per element.
//
// The shared PyfmiInterop library supplies the FmuInterop base and its
// InteropDeployment parameter port, so this example authors only its own
// interface.  Deployment defaults are initialization configuration: the
// master binds them before fmi2EnterInitializationMode, and they never become
// wire fields.  Structural facts (step size, serialization backend, role) stay
// build-time attributes and are deliberately not parameters.
package ActuatorLinkExample {
  private import ScalarValues::*;
  private import PyfmiInterop::*;

  port def Command {
    attribute setpoint : Real;
    attribute mode : Integer;
    attribute enable : Boolean;
    attribute gains : Real[3];
  }

  port def Feedback {
    attribute position : Real;
    attribute status : Integer;
    attribute healthy : Boolean;
    attribute samples : Real[2];
  }

  part def ActuatorLink :> FmuInterop {
    in port command : Command;
    out port feedback : Feedback;
  }
}
