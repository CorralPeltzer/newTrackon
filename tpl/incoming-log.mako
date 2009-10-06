<%! from time import time %>
<%inherit file="base.mako"/>

<div class=grid_12>
<h2 id=page-heading>Log of Newly Submitted Trackers and their Statuses</h2>

% if msgs:
<table cellspacing=0 class=sortable>
    <thead><tr>
        <th>msg</th>
    </tr></thead>
    % for m in msgs:
        ## Should remove the decode call now that we decode error strings on input.
        <tr><td>${m.decode('utf-8', 'ignore')|n}</td></tr>
    % endfor
</table>

% endif
</div>


