// Iterative development, revision 3: the output port gains a clipped field.
// The hand-written model still assigns only lower and upper, so the new
// member is left without an equation and the build refuses.
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
    attribute clipped : Boolean;
  }

  port def Gains :> ParameterInterface {
    attribute gain : Real = 2.0;
  }

  part def Scaler {
    in port parameters : Gains;
    in port command : Signal;
    out port limited : Limits;
  }

  part def Root {
    part scaler : Scaler;
  }
}
