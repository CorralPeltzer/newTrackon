<%! from time import time %>
<%inherit file="base.mako"/>
<%page cached="False"/>


<div class=grid_12>
<h2 id=page-heading>Tracking the Trackers</h2>

<p>Trackon is a service to monitor the status and health of existing open and public trackers that anyone can use.</p>

<p>Stil experimental, <b>please do not post to torrent freak or any public
forum yet! ;)</b></p>
</div>

<div class=grid_12>
<table cellspacing=0 class=sortable>
    <thead><tr>
        <th>Tracker's Announce URL</th>
        <th>Latency</th>
        <th>Checked</th>
        <th>Status</th>
        <th>Interval</th>
    </tr></thead>

% if trackers:
    % for a in trackers:
        <% t = trackers[a] %>
        % if not t:
            <% continue %>
        % endif
        <tr>
            <td>${a}</td>
            <td>${"%.3f" % t['latency']}</td>
            <td>${(int(time()) - t['updated']) / 60}m ago</td>
        % if 'error' in t:
            <td class=error><b title="${t['error']}">Error!</b></td>
            <td></td>
        % else:
            <% r = t['response'] %>
            % if r['peers']:
                <td class=excellent><b>Excellent!</b></td>
            % else:
                <td class=ok><b>Ok</b></td>
            % endif
            <td>${r.get('interval', '-')}</td>
            ##cell("%d/%d/%d %d:%d:%d"%(gmtime(s['updated'])[:6]))
        % endif

        </tr>
    % endfor
% endif

</table>
</div>


<form method="POST" class=grid_12>
    <fieldset class="login">

% if new_tracker_error:
        <p><b>Could not add tracker: ${new_tracker_error | h}</b></p>
% endif 
        <input type="text" name="tracker-address" value="" size=64>
        <input type="submit" value="Add Tracker">
    </fieldset>
</form>

<div class=grid_12>

<p>If you post a new tracker, please allow for a few minutes while we gather
statistics before it is added to the list.</p>

</div>


<div class="grid_12 center">
<img src='http://upload.wikimedia.org/wikipedia/commons/3/3e/Nine-Dragons1.jpg' title='The Trackon' alt='The Trackon' />
</div>
