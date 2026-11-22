% The hand-authored half of the Simulink seam.
%
% generate_types.py owns the bus definitions and the port manifest; this file
% owns the model. Nothing here is rewritten by the generator, so a human keeps
% the equations while regeneration refreshes the contract around them.
%
% The model is rebuilt from scratch on every run. It uses the generated bus
% types by name only: an inport `u` carrying a `Signal`, a bus selector that
% reads `value`, a gain of 2.0 (taken from Scale.parameters.gain in
% ports.json), and a bus creator feeding the outport `y` as a `Signal`.
% check_interface.m is what notices when that contract has drifted.

model = 'ScaleModel';

if bdIsLoaded(model)
    close_system(model, 0);
end
if exist([model '.slx'], 'file')
    delete([model '.slx']);
end
new_system(model);
load_system(model);

add_block('simulink/Sources/In1', [model '/u'], ...
    'Port', '1', 'OutDataTypeStr', 'Bus: Signal');
add_block('simulink/Signal Routing/Bus Selector', [model '/Selector'], ...
    'OutputSignals', 'value');
add_block('simulink/Math Operations/Gain', [model '/Gain'], 'Gain', '2.0');
add_block('simulink/Signal Routing/Bus Creator', [model '/Creator'], ...
    'Inputs', 'value');
add_block('simulink/Sinks/Out1', [model '/y'], ...
    'Port', '1', 'OutDataTypeStr', 'Bus: Signal');

add_line(model, 'u/1', 'Selector/1');
add_line(model, 'Selector/1', 'Gain/1');
gain_line = add_line(model, 'Gain/1', 'Creator/1');
set_param(gain_line, 'Name', 'value');
add_line(model, 'Creator/1', 'y/1');

% A silently unconnected port is exactly the failure this prototype exists to
% make loud, so make Simulink itself complain as well.
set_param(model, ...
    'SolverType', 'Fixed-step', ...
    'Solver', 'FixedStepDiscrete', ...
    'FixedStep', '0.01', ...
    'StartTime', '0', ...
    'StopTime', '1', ...
    'UnconnectedInputMsg', 'error', ...
    'UnconnectedOutputMsg', 'error', ...
    'UnconnectedLineMsg', 'error');

save_system(model);
fprintf('built %s\n', model);
