<!DOCTYPE HTML>
<%! from time import time %>
<%inherit file="base.mako"/>

<div class=grid_12>

<h2 id=page-heading>Tracking the Trackers</h2>

<p>Trackon is a service to monitor the status and health of existing open and public trackers that anyone can use. A meta-tracker if you will. You can add any of the tracker announce URLs listed here to any of your torrents, or submit any other open/public trackers you might know of.</p>
<p>To download a torrent client ready list of all trackers with more than 90% of uptime, go to the <a href="/list">List</a> section.
</div>

<div class=grid_12>
<table cellspacing=0 cellpadding=0 class=sortable>
    <thead><tr>
      <th>Tracker URL</th>
      <th>IP address</th>
      <th class="sortable">Country</th>
      <th class="sortable">Network</th>
      <th class="sorttable_numeric">Latency <span class=units></span></th>
      <th class="sorttable_numeric">Last checked <span class=units></span></th>
      <th class="sorttable_numeric">Update interval <span class=units></span></th>
      <th>Status</th>
      <th class="sortable">Added </th>
      <th class="sorttable_numeric">Uptime *</th>
    </tr></thead>

    <% lt = dt = 0 %>
    % if trackers:
        % for t in trackers:
            % if not t:
                <% continue %>
            % endif
                <td>${t['url']}</td>
                <td>${t['ip']}</td>
                <td>${t.get('country', 'Unknown')}</td>
                <td>${t.get('network', 'Unknown')}</td>
                <td class=right>${"%.3f" % t['latency']} sec</td>
                <td class=right>${(int(time()) - t.get('updated', 'Unknown')) / 60} min ago</td>
                <td class=center>~${t['interval']/60} min (${t['interval']} sec)</td>
                % if t['status'] == 1:
                    <td sorttable_customkey="1" class=up><b>Working</b></td>
                    <% lt += 1 %>
                % else:
                    <td sorttable_customkey="2" class=down><b>Down</b></td>
                    <% dt += 1 %>
                % endif
                <td class=right>${t['added']}</td>
                <td class=right>${"%.2f" % t['uptime']}%</td>
            </tr>
        % endfor

        <caption style="text-align: right;"><b>Live trackers</b>: ${lt} / <b>Trackers down</b>: ${dt} / <b>Total trackers</b>: ${len(trackers)}</caption>

    % endif

</table>
<caption style="text-align: right;">* Based on the last 1000 checks. The time depends on the update interval set by the tracker, and can vary from 6 to 40 days.</caption>
</div>


<div class=grid_12>
<hr>
<a name="new"></a>
<form method="POST" action="/" class="grid_12 center">

% if new_tracker_error:
        <p><b>Could not add tracker: ${new_tracker_error | h}</b></p>
% endif
        <input type="text" name="tracker-address" value="" size=64>
        <input type="submit" value="Add Tracker">
<p>If you post a new tracker, please allow for a few seconds while we gather
statistics before it is added to the list.</p>
</form>
</div>
<%def name="extraheaders()"><script type="text/javascript" src="/static/js/sorttable.js"></script></%def>
