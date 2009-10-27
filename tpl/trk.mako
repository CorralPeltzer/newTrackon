<%inherit file="base.mako"/>

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
</dl>

<table>
    <thead><tr>
        <th>Time
        <th>Latency
        <th>Error
    </tr></thead>
%for l in logs:
<% from time import ctime %>
    <tr>
    <td>${ctime(l['updated'])}
    <td>${l['latency']}
    <td>${l.get('error','Just fine!')}
    </tr>
%endfor
</table>

</div>
