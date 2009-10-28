<%inherit file="base.mako"/>
<% from time import ctime, time %>

<div class=grid_12>
<h2 id=page-heading>${trk['title']} Info</h2>
<dl>
    <dt>Announce URL
    <dd>${trka|h}

%if trk.get('ssl', False):
    <dt>SSL Announce URL
    <dd>${trka.replace('http://', 'https://')|h}
%endif

%if trk.get('home', False):
    <dt>Homepage
    <dd>${trk['home']|h}
%endif

%if trk.get('error', False):
    <dt>Error
    <dd>${trk['error']|h}
%endif

%if trk.get('next-check', False):
    <dt>Next check scheduled in...
    <dd>${(trk['next-check']-int(time()))/60|h} minutes.
%endif
</dl>

<table>
    <thead><tr>
        <th>Time
        <th>Latency
        <th>Error
    </tr></thead>
%for l in logs:
    <tr>
    <td class=center>${ctime(l['updated'])}
    <td class=right>${"%.6f"%l['latency']}
    <td>${l.get('error','Just fine!')}
    </tr>
%endfor
</table>

</div>


<%def name="title()">${trk['title']} - Tracker Info</%def>
