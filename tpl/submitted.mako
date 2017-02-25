<%! from time import time %>
<%inherit file="base.mako"/>

<div class=grid_12>
<h2 id=page-heading>Log of Newly Submitted Trackers</h2>
<h3> Number of trackers in the queue: ${size} </h3>
${submitted}
</div>
<%def name="title()">Log of submitted trackers</%def>
