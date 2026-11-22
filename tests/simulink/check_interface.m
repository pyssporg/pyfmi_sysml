% The drift oracle for the Simulink seam.
%
% The model is hand-owned, the bus types and ports.json are generated. In
% Simulink a renamed, added, removed, or reordered port is silent, so compare
% the loaded model against the manifest and fail with both sides named.
%
% The default manifest is ports.json in the current directory (run.sh runs
% MATLAB inside build/). Set PORTS_JSON to point somewhere else; run.sh does
% that in the drift stage. Bus objects must already be in the base workspace,
% loaded by defineBusTypes.m.

manifest_path = getenv('PORTS_JSON');
if isempty(manifest_path)
    manifest_path = 'ports.json';
end
manifest = jsondecode(fileread(manifest_path));

names = fieldnames(manifest);
if numel(names) ~= 1
    error('check_interface:ambiguousManifest', ...
        'manifest %s describes %d components, expected exactly 1', ...
        manifest_path, numel(names));
end
component = manifest.(names{1});

model = 'ScaleModel';
load_system(model);

ports = component.ports;
if isempty(ports)
    ports = struct('name', {}, 'direction', {}, 'bus', {}, 'fields', {});
end

check_ports('Inport', 'in', ports, model);
check_ports('Outport', 'out', ports, model);

for k = 1:numel(ports)
    check_bus(ports(k));
end

fprintf('interface matches %s\n', manifest_path);


function check_ports(block_type, direction, ports, model)
    expected = ports(strcmp({ports.direction}, direction));
    found = find_system(model, 'SearchDepth', 1, 'BlockType', block_type);
    found = sort_by_port(found, model);
    total = max(numel(expected), numel(found));
    for i = 1:total
        if i <= numel(found)
            actual = get_param(found{i}, 'Name');
        else
            actual = '<missing>';
        end
        if i <= numel(expected)
            wanted = expected(i).name;
        else
            wanted = '<missing>';
        end
        if ~strcmp(actual, wanted)
            error('check_interface:portMismatch', ...
                'port %d: model ''%s'', manifest ''%s''', i, actual, wanted);
        end
        got = get_param(found{i}, 'OutDataTypeStr');
        want = ['Bus: ' expected(i).bus];
        if ~strcmp(got, want)
            error('check_interface:dataTypeMismatch', ...
                'port %d ''%s'': model DataType ''%s'', manifest ''%s''', ...
                i, wanted, got, want);
        end
    end
end

function ordered = sort_by_port(blocks, model)
    if isempty(blocks)
        ordered = {};
        return;
    end
    numbers = zeros(1, numel(blocks));
    for k = 1:numel(blocks)
        numbers(k) = str2double(get_param(blocks{k}, 'Port'));
    end
    [~, order] = sort(numbers);
    ordered = blocks(order);
end

function check_bus(port)
    bus_name = port.bus;
    if evalin('base', sprintf('exist(''%s'', ''var'')', bus_name)) == 0
        error('check_interface:missingBus', ...
            'port ''%s'': bus ''%s'' does not exist', port.name, bus_name);
    end
    bus_object = evalin('base', bus_name);
    if ~isa(bus_object, 'Simulink.Bus')
        error('check_interface:missingBus', ...
            'port ''%s'': ''%s'' is not a Simulink.Bus', ...
            port.name, bus_name);
    end

    fields = port.fields;
    if isempty(fields)
        fields = struct('name', {}, 'type', {}, 'value', {});
    end
    elements = bus_object.Elements;
    if numel(elements) ~= numel(fields)
        error('check_interface:busShapeMismatch', ...
            'bus ''%s'': model has %d elements, manifest %d', ...
            bus_name, numel(elements), numel(fields));
    end
    for i = 1:numel(fields)
        if ~strcmp(elements(i).Name, fields(i).name)
            error('check_interface:busElementMismatch', ...
                'bus ''%s'' element %d: model ''%s'', manifest ''%s''', ...
                bus_name, i, elements(i).Name, fields(i).name);
        end
        want = matlab_data_type(fields(i).type);
        if ~strcmp(elements(i).DataType, want)
            error('check_interface:busTypeMismatch', ...
                'bus ''%s'' element %d ''%s'': model DataType ''%s'', manifest ''%s''', ...
                bus_name, i, fields(i).name, elements(i).DataType, want);
        end
    end
end

function data_type = matlab_data_type(type_name)
    switch type_name
        case 'Real'
            data_type = 'double';
        case 'Integer'
            data_type = 'int32';
        case 'Boolean'
            data_type = 'boolean';
        case 'String'
            data_type = 'string';
        otherwise
            error('check_interface:unknownType', ...
                'unknown manifest type ''%s''', type_name);
    end
end
