// A parameter set applied with bind, and the default experiment carried by a
// typed attribute container instead of retired control tags.
package Applied {
  private import ScalarValues::*;
  private import PysspCore::*;

  port def Signal {
    attribute value : Real;
  }

  port def GainParameters :> ParameterInterface {
    attribute gains : Real[2] = (1.0, 2.5);
  }

  attribute def TunedSet :> ParameterSet {
    attribute gains : Real[2] = (9.0, 9.5);
  }

  attribute def PlantDefaults :> DefaultExperiment {
    attribute startTime : Real = 0.0;
    attribute stopTime : Real = 10.0;
    attribute stepSize : Real = 0.1;
  }

  part def Scale {
    in port parameters : GainParameters;
    in port u : Signal;
    out port y : Signal;
  }

  part def AppliedComposition {
    part scale : Scale;
    attribute tuned : TunedSet;
    attribute defaults : PlantDefaults;
    bind scale.parameters = tuned;
  }
}
