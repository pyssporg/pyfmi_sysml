within GeneratedInterfaces;

partial model Tank_Interface
  parameter Real capacity = 3160;
  parameter Real reserve = 0.08;
  input GeneratedInterfaces.Rate supply;
  output GeneratedInterfaces.LevelState level;
end Tank_Interface;
