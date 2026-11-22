within GeneratedInterfaces;

partial model Bus_Interface
  input GeneratedInterfaces.Actuation actuation;
  input GeneratedInterfaces.Orientation orientation_in;
  input GeneratedInterfaces.Position position_in;
  GeneratedInterfaces.Orientation shared;
  output GeneratedInterfaces.Orientation orientation_out;
  output GeneratedInterfaces.Position position_out;
  output GeneratedInterfaces.StatusPacket status;
end Bus_Interface;
