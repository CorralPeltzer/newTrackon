<%! from time import time %>
<%inherit file="base.mako"/>

<link rel="stylesheet" type="text/css" href="https://cdn.datatables.net/v/dt/jq-2.2.4/dt-1.10.13/r-2.1.0/datatables.min.css"/>

<script type="text/javascript" src="https://cdn.datatables.net/v/dt/jq-2.2.4/dt-1.10.13/r-2.1.0/datatables.min.js"></script>

<script type="text/javascript" src="//cdn.datatables.net/plug-ins/1.10.13/sorting/natural.js"></script>

<script type="text/javascript" src="//cdn.datatables.net/plug-ins/1.10.13/sorting/date-eu.js"></script>


<script type="text/javascript">
$(document).ready( function () {
    $('#trackon_table').DataTable( {
    "pageLength": 25,
    "order": [[ 1, 'desc' ], [ 9, 'asc' ]],
    "columnDefs": [
        { "type": "natural", targets: [3, 4, 5, 8] },
        { "type": "date-eu", targets: 9 }
    ]
    } );
    document.getElementById('trackon_table').style.visibility = 'visible';
} );
</script>

<div class="grid_12">

<h2 id=page-heading>Tracking the Trackers</h2>
<p>newTrackon is a service to monitor the status and health of existing open and public trackers that anyone can use. A meta-tracker if you will. You can add any of the tracker announce URLs listed here to any of your torrents, or submit any other open/public trackers you might know of.</p>
<p>To download a client-ready list of all trackers with more than 95% of uptime, go to the <a href="/list">List</a> section.
</div>

<div class="grid_12">
<hr>
<p><a name="new"></a>
<form method="POST" action="/">
    <input type="text" name="tracker-address" value="" size=64>
    <input type="submit" value="Add Tracker">
</form></p>
<p>You can submit multiple trackers separated by whitespaces. If you post new trackers, please wait a few minutes while we gather data before it is added to the list,
 or check the <a href="/incoming-log">Incoming</a> section.</p>

</div>

<div class="grid_12">
<table id="trackon_table" class="display responsive">
    <thead><tr>
      <th>Tracker URL</th>
      <th class="sorttable_numeric">Uptime *</th>
      <th>Status</th>
      <th class="sorttable_numeric">Checked</th>
      <th class="sorttable_numeric">Update interval</th>
      <th>IP address</th>
      <th class="sortable">Country</th>
      <th class="sortable">Network</th>
      <th class="sorttable_numeric"><span title="Announce time">Time</span></th>
      <th class="right">Added </th>
    </tr></thead>

    <% lt = dt = 0 %>
    % if trackers:
        % for t in trackers:
            <tr>
            % if not t:
                <% continue %>
            % endif
                <td>${t['url']}</td>
                <td>${"%.2f" % t['uptime']}%</td>
                % if t['status'] == 1:
                    <td class="up"><b>Working</b></td>
                    <% lt += 1 %>
                % else:
                    <td class="down"><b>Down</b></td>
                    <% dt += 1 %>
                % endif
                <td>${(int(time()) - t.get('updated', 'Unknown')) / 60} min ago</td>
                <td>~${t['interval']/60} min (${t['interval']} sec)</td>
                <td>${t['ip']}</td>
                <td>${t.get('country', 'Unknown')}</td>
                <td>${t.get('network', 'Unknown')}</td>
                <td>${t['latency']} ms</td>
                <td class="right">${t['added']}</td>
            </tr>
        % endfor
    % endif
<caption style="text-align: right;"><b>Live trackers</b>: ${lt} / <b>Trackers down</b>: ${dt} / <b>Total trackers</b>: ${len(trackers)}</caption>
</table>
<noscript>
    <style>#trackon_table{visibility:visible}</style>
</noscript>
<p style="text-align: right;">* Based on the last 1000 checks. The time depends on the update interval set by the tracker, and can vary from 6 to 40 days.</p>
</div>

<%def name="extraheaders()"></%def>
