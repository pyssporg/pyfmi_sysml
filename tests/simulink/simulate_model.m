% Behaviour check for the hand model: put 3 on u.value and require the bus
% field y.value to end at 6, because the hand model applies a gain of 2.0.
% Structure is check_interface.m's job; this script only asserts the numbers.
%
% The inport and its selector stand for u.value; for this run they are
% replaced by a Constant of 3, which is what u.value would carry. Only the
% in-memory copy changes, so the saved model still has the hand-authored
% inport that check_interface.m inspects.

model = 'ScaleModel';
load_system(model);

delete_line(model, 'u/1', 'Selector/1');
delete_line(model, 'Selector/1', 'Gain/1');
delete_block([model '/u']);
delete_block([model '/Selector']);
add_block('simulink/Sources/Constant', [model '/Three'], 'Value', '3');
add_line(model, 'Three/1', 'Gain/1');

set_param(model, ...
    'StopTime', '1', ...
    'SaveOutput', 'on', ...
    'SaveFormat', 'Dataset', ...
    'OutputSaveName', 'yout', ...
    'SignalLogging', 'off');

out = sim(model);
element = out.yout.get(1);
if ~isfield(element.Values, 'value')
    error('simulate_model:wrongOutput', ...
        'outport y did not carry a Signal field named value');
end
final = element.Values.value.Data(end);
if final ~= 6
    error('simulate_model:wrongOutput', ...
        'final y.value is %g, expected 6 (u.value 3 x gain 2)', final);
end
fprintf('simulated: final y.value = %g\n', final);
close_system(model, 0);
