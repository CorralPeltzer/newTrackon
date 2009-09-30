<%! from time import time %>
<%inherit file="base.mako"/>

<div class=grid_12>
<h2 id=page-heading>Log of Newly Submitted Trackers and their Statuses</h2>

% if msgs:
<table cellspacing=0 class='sortable grid_12'>
    <thead><tr>
        <th>msg</th>
    </tr></thead>
    % for m in msgs:
        <tr><td>${m|h}</td></tr>
    % endfor
</table>
% endif
</div>


