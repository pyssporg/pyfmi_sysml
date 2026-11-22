// Iterative development, revision 1: one scalar gain, one input port, one
// output port with two fields. The Modelica package generated from this
// architecture is the interface the hand-written model starts from.
package SignalScale {
  private import ScalarValues::*;
  private import PysspCore::*;

  port def ParameterInterface;
  attribute def ParameterSet;

  port def Signal {
    attribute value : Real;
  }

  port def Limits {
    attribute lower : Real;
    attribute upper : Real;
  }

  port def Gains :> ParameterInterface {
    attribute gain : Real = 2.0;
  }

  part def Scaler {
    in port parameters : Gains;
    in port raw : Signal;
    out port limited : Limits;
  }

  part def Root {
    part scaler : Scaler;
  }
}
