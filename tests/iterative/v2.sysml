// Iterative development, revision 2: the input port is renamed from raw to
// command. Regenerating moves the generated partial model; the hand-written
// model keeps referring to the old name and stops building.
package SignalScale {
  private import ScalarValues::*;
  private import PysspCore::*;
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
    in port command : Signal;
    out port limited : Limits;
  }

  part def Root {
    part scaler : Scaler;
  }
}
