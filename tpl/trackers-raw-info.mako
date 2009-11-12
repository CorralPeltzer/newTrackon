<%! from time import time %>
<%inherit file="base.mako"/>

<div class=grid_12>
<h2 id=page-heading>The Raw Data</h2>

<p>This is the raw data received from the trackers, for research and debugging purposes.</p>

</div>

% if trackers:
<div class=grid_12><table cellspacing=0 class=sortable>
    <thead><tr>
        <th>Tracker</th>
        <th>Request</th>
        <th>Response</th>
    </tr></thead>

    % for a in trackers:
        <% t = trackers[a] %>
        % if not t:
            <% continue %>
        % endif

        <tr>
            <td>${a}</td>
            <td>${t.get('query-string', '')}</td>
        % if 'error' in t:
            <td><b>Error:</b> ${t['error']|h}</td>
        % else:
            <td>${repr(t['response'])|h}</td>
        % endif

        </tr>
    % endfor

% endif

</table></div>

<%def name="title()">Raw tracker responses.</%def>
