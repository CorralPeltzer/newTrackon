<%inherit file="base.mako"/>
<%page cached="False"/>

<div class=grid_12>
% for t in trackers_info:
    <% ti = trackers_info[t] %>
    <form action="/admin" method="POST"><fieldset>
        <legend>${t}</legend>
        %if t in errors:
            <ul>
            %for e in errors[t]:
                <li>${e|h}
            %endfor
            </ul>
        %endif
        <input type="hidden" name="address" value="${t}">
        <label>Title:<input type="text" name="title" value="${ti.get('title', '')}"></label>
        <label>Home:<input type="text" name="home" value="${ti.get('home', '')}"></label>
        <label>Name:<input type="text" name="name" value="${ti.get('name', '')}"></label>
        <label style="float:left;">Description:<br><textarea name="descr" cols=42 rows=5>${ti.get('descr', '')}</textarea></label>
        <label style="float:left;">Aliases:<br><textarea name="alias" cols=42 rows=5>${'\n'.join(ti.get('alias', []))|h}</textarea></label>
        <div style="float:left;">
        <input type="submit" name="action" value="X"><b>Delete!</b>
        <hr><br>
        <input type="submit" name="action" value="Update">
        </div>
    </fieldset></form>
% endfor
</div>

<!--<div class=grid_12>
    <form action="/admin" method="POST"><fieldset>
        <input type="text" name="address" value="">
        <input type="submit" name="action" value="New">
    </fieldset></form>
</div>-->
