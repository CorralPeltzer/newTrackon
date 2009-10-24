<%! from time import time %>
<%inherit file="base.mako"/>

<div class=grid_12>

<h2 id=page-heading>Tracking the Trackers</h2>

<p>Trackon is a service to monitor the status and health of existing open and public trackers that anyone can use. A meta-tracker if you will. You can add any of the tracker announce URLs listed here to any of your torrents, or submit any other open/public trackers you might know of.</p>

<p>Still experimental, <b>please do not post to torrent freak yet! ;)</b></p>
</div>

<div class=grid_12>
<table cellspacing=0 cellpadding=0 class=sortable>
    <thead><tr>
        <th>Tracker</th>
        <th>Announce URL</th>
        <th>SSL</th>
        <th class="sorttable_numeric">Latency <span class=units></span></th>
        <th class="sorttable_numeric">Checked <span class=units></span></th>
        <th>Status</th>
        <th class="sorttable_numeric">Interval / Min</th>
        <th class="sorttable_numeric">Uptime</th>
    </tr></thead>

<% lt = dt = 0 %>
% if trackers:
    % for a in trackers:
        <% t = trackers[a] %>
        % if not t:
            <% continue %>
        % endif
        <tr>
            <td>${t.get('title', a.split('/')[2])}</td>
            <td>${a}</td>
            <td>
                % if t.get('ssl', False):
                    Yes
                % else:
                    No
                % endif
                ##(${t.get('ssl', '-')})
            </td>
            <td class=right>${"%.3f" % t['latency']} sec</td>
            <td class=right>${(int(time()) - t['updated']) / 60} min ago</td>
        % if 'error' in t:
            <% dt += 1 %>
            <td sorttable_customkey="3" class=error><b title="${t['error']|h}">Error!</b></td>
            <td class=right>- / -</td>
        % else:
            <% lt += 1 %>
            <% r = t['response'] %>
            % if r['peers']:
                <td sorttable_customkey="1" class=excellent><b>Excellent!</b></td>
            % else:
                <td sorttable_customkey="2" class=ok><b>Ok</b></td>
            % endif
            <td class=right>${r.get('interval', '-')} / ${r.get('min interval', '-')}</td>
        % endif
            <td class=right>${t.get('uptime', '-')}%</td>

        </tr>
    % endfor

    <caption style="text-align: right;"><b>Live trackers</b>: ${lt} / <b>Trackers down</b>: ${dt} / <b>Total trackers</b>: ${len(trackers)}</caption>

% endif

</table>

Possible status values:
<ul>
    <li><b>Excellent</b>: The tracker was reachable, returned a valid response <i>that included peers</i>.

    <li><b>Ok</b>: The tracker was reachable, and while it returned a valid response, it didn't include any peers.

    <li><b>Error</b>:The tracker was either unreachable or returned some kind of error. For a detailed error message see tooltip.
</ul>

</div>


<div class=grid_12>

<form method="POST" class=grid_12>
    <fieldset class="login center">

% if new_tracker_error:
        <p><b>Could not add tracker: ${new_tracker_error | h}</b></p>
% endif 
        <input type="text" name="tracker-address" value="" size=64>
        <input type="submit" value="Add Tracker">
<hr style="margin: 0.8em">
If you post a new tracker, please allow for a few minutes while we gather
statistics before it is added to the list.
    </fieldset>
</form>

</div>


<%def name="extraheaders()"><script type="text/javascript" src="http://www.kryogenix.org/code/browser/sorttable/sorttable.js"></script></%def>
