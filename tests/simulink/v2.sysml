// Drifted copy of tests/fixtures/minimal/minimal.sysml used by stage 4 of
// run.sh: the input port `u` is renamed to `command`. Everything else is
// unchanged, so the only drift the checker must report is the port name.
package Minimal {
  private import ScalarValues::*;
  private import PysspCore::*;
  port def Signal {
    attribute value : Real;
  }

  port def GainParameters :> ParameterInterface {
    attribute gain : Real = 2.0;
  }

  part def Scale {
    in port parameters : GainParameters;
    in port command : Signal;
    out port y : Signal;
  }

  part def Root {
    part scale : Scale;
  }
}
