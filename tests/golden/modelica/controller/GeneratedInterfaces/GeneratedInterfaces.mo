within GeneratedInterfaces;
package GeneratedInterfaces
  connector Command
    Real manual;
    Real auto;
    Integer mode;
  end Command;

  connector Status
    Integer code;
  end Status;

  connector Throttle
    Real demand;
    Boolean enabled;
  end Throttle;

end GeneratedInterfaces;
