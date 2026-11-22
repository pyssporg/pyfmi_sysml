within GeneratedInterfaces;

partial model Controller_Interface
  parameter Real gains[2] = {1, 2.5};
  parameter String label = "nominal";
  input GeneratedInterfaces.Command command;
  output GeneratedInterfaces.Throttle throttle;
  output GeneratedInterfaces.Status status;
end Controller_Interface;
