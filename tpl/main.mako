<%! from time import time %>
<%inherit file="base.mako"/>
<%page cached="False"/>


<div class=grid_12>
<p>Stil experimental, <b>please do not post to torrent freak or any public
forum yet! ;)</b></p>
</div>

% if trackers:
<table cellspacing=0 class='sortable grid_12'>
    <thead><tr>
        <th>Tracker</th>
        <th>Latency</th>
        <th>Checked</th>
        <th>Announce</th>
        <th>Up?</th>
        <th>Interval</th>
        <th>...</th>
    </tr></thead>
    % for a in trackers:
        <% t = trackers[a] %>
        % if not t:
            <% continue %>
        % endif
        <tr>
            <td>${a.split('/')[2]}</td>
            <td>${"%.3f" % t['latency']}</td>
            <td>${(int(time()) - t['updated']) / 60}m ago</td>
            <td><a href="${a}" title="">Link</a></td>

        % if 'error' in t:
            <td><b title="${t['error']}">Error!</b></td>
            <td></td> <td></td>
        % else:
            <% r = t['response'] %>
            <td><b>UP!</b></td>
            <td>${r.get('interval', '-')}</td>
            ##cell("%d/%d/%d %d:%d:%d"%(gmtime(s['updated'])[:6]))
            <td>${repr(r)}</td>
        % endif

        </tr>
    % endfor
% endif

</table>


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
