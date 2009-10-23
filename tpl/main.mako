<%! from time import time %>
<%inherit file="base.mako"/>

<div class=grid_12>
<div style="text-align: right; padding-top: 1px;"><script type="text/javascript">var addthis_disable_flash = true; var addthis_pub="uriell";</script> <a href="http://www.addthis.com/bookmark.php?v=20" onmouseover="return addthis_open(this, '', '[URL]', '[TITLE]')" onmouseout="addthis_close()" onclick="return addthis_sendto()"><img src="http://s7.addthis.com/static/btn/lg-share-en.gif" width="125" height="16" alt="Bookmark and Share" style="border:0"/></a><script type="text/javascript" src="http://s7.addthis.com/js/200/addthis_widget.js"></script></div>

<h2 id=page-heading>Tracking the Trackers</h2>

<p>Trackon is a service to monitor the status and health of existing open and public trackers that anyone can use. A meta-tracker if you will. You can add any of the tracker announce URLs listed here to any of your torrents, or submit any other open/public trackers you might know of.</p>

<p>Still experimental, <b>please do not post to torrent freak yet! ;)</b></p>
</div>

<div class=grid_12>
<table cellspacing=0 class=sortable>
    <thead><tr>
        <th>Tracker</th>
        <th>Announce URL</th>
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

    <p><b>Live trackers</b>: ${lt} / <b>Trackers down</b>: ${dt} / <b>Total trackers</b>: ${len(trackers)}</p>

% endif

</table>

Possible status values:
<ul>
    <li><b>Excellent</b>: The tracker was reachable, returned a valid response <i>that included peers</i>.

    <li><b>Ok</b>: The tracker was reachable, and while it returned a valid response, it didn't include any peers.

    <li><b>Error</b>:The tracker was either unreachable or returned some kind of error. For a detailed error message see tooltip.
<ul>

</div>


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

<div class=grid_12>


</div>


<div class="center">
<img style="border: solid black 0.4em" src='http://upload.wikimedia.org/wikipedia/commons/3/3e/Nine-Dragons1.jpg' title='Trago is the mascot dragon of Trackon.org' alt='Trago the dragon' />
</div>
