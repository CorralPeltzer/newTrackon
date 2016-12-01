<%! from time import time %>
<%inherit file="base.mako"/>

<div class=grid_12>
<h2 id=page-heading>Log of Newly Submitted Trackers</h2>
<h3> Number of trackers in the queue: ${size} </h3>
${incoming}
</div>
<%def name="title()">Log of incoming trackers.</%def>

