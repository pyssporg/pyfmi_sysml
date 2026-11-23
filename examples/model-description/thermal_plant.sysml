// A two-component thermal plant: one exported FMI model per leaf part.
// `Sensor` scales a raw reading; `Valve` limits an opening command.
package ThermalPlant {
  private import ScalarValues::*;
  private import PysspCore::*;

  port def SensorParameters :> ParameterInterface {
    attribute gain : Real = 1.0;
    attribute offset : Real = 0.0;
  }

  port def Temperature {
    attribute value : Real;
  }

  part def Sensor {
    in port parameters : SensorParameters;
    in port raw : Temperature;
    out port measured : Temperature;
  }

  port def ValveParameters :> ParameterInterface {
    attribute limit : Real = 1.0;
  }

  port def OpeningCommand {
    attribute open : Real;
  }

  port def Position {
    attribute value : Real;
  }

  part def Valve {
    in port parameters : ValveParameters;
    in port command : OpeningCommand;
    out port position : Position;
  }

  part def ThermalPlantComposition {
    part sensor : Sensor;
    part valve : Valve;
  }
}
