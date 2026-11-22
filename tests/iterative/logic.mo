within GeneratedInterfaces;

// Hand-written model logic, revision 1: one equation per output member.
model Scaler
  extends Scaler_Interface;
equation
  limited.lower = min(raw.value*gain, 0.0);
  limited.upper = max(raw.value*gain, 0.0);
end Scaler;
