<%inherit file="base.mako"/>
<link rel="stylesheet" href="https://cdn.datatables.net/v/bs/dt-1.10.15/r-2.1.1/datatables.min.css" integrity="sha256-2W/3LtLvI/CvYx3b+FekV7aKSJqyjUJcMibC8Pwe1Ug=" crossorigin="anonymous" />
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/flag-icon-css/2.8.0/css/flag-icon.min.css" integrity="sha256-EQjZwW4ljrt9dsonbyX+si6kbxgkVde47Ty9FQehnUg=" crossorigin="anonymous" />
<script src="https://cdn.datatables.net/v/bs/dt-1.10.15/r-2.1.1/datatables.min.js" integrity="sha256-KyEwc9kHefOLZrGKuj1mUHGp400HdjT6+0rQpHoIovs=" crossorigin="anonymous"></script>
<script src="https://cdn.datatables.net/plug-ins/1.10.15/sorting/natural.js" integrity="sha256-N3f4zkaAHf18uJNlRncQ+PPQnwPcICM82tJ/DQkDjYY=" crossorigin="anonymous"></script>
<script src="https://cdn.datatables.net/plug-ins/1.10.15/sorting/date-eu.js" integrity="sha256-lPEWTPmjv6eC5rGj5/11u7fH8NgPr72fDR7J9dN7Wug=" crossorigin="anonymous"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/moment.js/2.18.1/moment.min.js" integrity="sha256-1hjUhpc44NwiNg8OwMu2QzJXhD8kcj+sJA3aCQZoUjg=" crossorigin="anonymous"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/livestamp/1.1.2/livestamp.min.js" integrity="sha256-8r65KJgULBDiZhwDydfWrEkx3yyV/grGsGzaekobngI=" crossorigin="anonymous"></script>
<script>
$(document).ready( function () {
    $('#trackon_table').DataTable( {
    "pageLength": 25,
    "order": [[ 1, 'desc' ], [ 9, 'asc' ]],
    "columnDefs": [
        { "type": "natural", targets: [3, 4, 5, 8] },
        { "type": "date-eu", targets: 9 }
    ]
    } );
    $(".initially-hidden").css("visibility", "visible");
} );
</script>
<div class="container">
<h2 class="text-center">Tracking the Trackers</h2>
<p>newTrackon is a service to monitor the status and health of existing open and public trackers that anyone can use. A meta-tracker if you will. You can add any of the tracker announce URLs listed here to any of your torrents, or submit any other open/public trackers you might know of.</p>
<p><b>To get a client-ready list of all trackers with more than 95% of uptime, go to the <a href="/list">List</a> section.</b>

<hr>

<form method="POST" action="/">
    <div class="form-group">
      <textarea class="form-control" rows="2" id="textArea" name="new_trackers"></textarea>
      <span class="help-block">You can submit multiple trackers separated by whitespaces, newline, etc. If you post new trackers, please wait a few minutes while we gather data before it is added to the list,
       or check the <a href="/submitted">Submitted</a> section.</span>
    </div>
    <div class="form-group">
      <button type="submit" class="btn btn-primary">Submit</button>
    </div>
</form>




</div>
<div class="container-fluid table-responsive">
<table id="trackon_table" class="table display responsive table-striped table-bordered table-hover initially-hidden">
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
                <td>${t.url}</td>
                <td>${"%.2f" % t.uptime}%</td>
                % if t.status == 1:
                    <td class="up"><b>Working</b></td>
                    <% lt += 1 %>
                % else:
                    <td class="down"><b>Down</b></td>
                    <% dt += 1 %>
                % endif
                <td><span data-livestamp="${t.last_checked}"></span></td>
                <td>~${t.interval//60} min (${t.interval} sec)</td>
                <td>
                    % for ip in t.ip:
                        ${ip}<br>
                    % endfor
                </td>
                <td>
                    <% index = 0 %>
                    % for country in t.country:
                        <span class="flag-icon flag-icon-${t.country_code[index]}"></span> ${country}<br>
                        <%index += 1 %>
                    % endfor
                </td>
                <td>
                    % for network in t.network:
                        ${network}<br>
                    % endfor
                </td>
                <td class="right">${t.latency} ms</td>
                <td class="right">${t.added}</td>
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
<%def name="title()">newtrackon, Tracking the Trackers</%def>
