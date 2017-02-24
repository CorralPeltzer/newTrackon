<%! from time import time %>
<%inherit file="base.mako"/>

<div class=grid_12>
<h2 id=page-heading>Raw data</h2>

<p>This is the information about the response of the last 300 trackers contacted, for research and debugging purposes.
    These include only trackers already in the list. </p>
<p>The trackers are queried with a random hash.</p>

</div>

% if data:
<div class=grid_12>
<table cellspacing=0 class=sortable>
    <thead>
    <tr>
        <th>Time</th>
        <th>Tracker</th>
        <th>IP</th>
        <th>Result</th>
        <th>Response/Error</th>
    </tr>
    </thead>
    % for response in data:
    <tr>
        <td>${response['time']}</td>
        <td>${response['url']}</td>
        <td>${response['ip']}</td>
        % if response['status'] == 1:
            <td class="up"><b>Working</b></td>
        % else:
            <td class="down"><b>Down</b></td>
        % endif
        <td>${response['info']}</td>
    </tr>
    % endfor

% endif

</table>
        </div>

<%def name="title()">Raw tracker data</%def>
