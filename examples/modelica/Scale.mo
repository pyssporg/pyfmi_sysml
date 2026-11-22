within GeneratedInterfaces;

model Scale
  extends Scale_Interface;
equation
  y.value = gain * u.value;
end Scale;
