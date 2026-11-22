// A bench with three independently packaged interop units.
//
// Each `:> FmuInterop` leaf is one FMU: one part definition, one model, one
// payload message.  `System` only composes the three units; it is not marked
// `:> FmuModel`, so it is a container and never becomes an FMU itself.
package Bench {
  private import ScalarValues::*;
  private import PyfmiInterop::*;

  port def ActuatorCommand {
    attribute setpoint : Real;
    attribute mode : Integer;
    attribute enable : Boolean;
    attribute gains : Real[3];
  }

  port def ActuatorFeedback {
    attribute position : Real;
    attribute status : Integer;
    attribute healthy : Boolean;
    attribute samples : Real[2];
  }

  port def SensorRequest {
    attribute sample_rate : Real;
    attribute channel : Integer;
    attribute trigger : Boolean;
    attribute offsets : Real[2];
  }

  port def SensorReading {
    attribute measurement : Real;
    attribute count : Integer;
    attribute valid : Boolean;
    attribute window : Real[4];
  }

  port def ControllerInput {
    attribute measured : Real;
    attribute reference : Real;
    attribute mode : Integer;
    attribute enabled : Boolean;
    attribute weights : Real[3];
  }

  port def ControllerOutput {
    attribute command : Real;
    attribute effort : Real;
    attribute phase : Integer;
    attribute active : Boolean;
    attribute limits : Real[2];
  }

  part def ActuatorLink :> FmuInterop {
    in port command : ActuatorCommand;
    out port feedback : ActuatorFeedback;
  }

  part def SensorLink :> FmuInterop {
    in port request : SensorRequest;
    out port reading : SensorReading;
  }

  part def Controller :> FmuInterop {
    in port input : ControllerInput;
    out port output : ControllerOutput;
  }

  part def System {
    part actuator : ActuatorLink;
    part sensor : SensorLink;
    part controller : Controller;
  }
}
