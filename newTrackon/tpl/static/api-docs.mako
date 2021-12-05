<%inherit file="../base.mako"/>
<div class="container rapidoc">
<rapi-doc
    spec-url="api.yml"
    theme=light
    render-style=view
    font-size=largest
    show-header=false
    regular-font=roboto
    layout=column
    default-schema-tab=example
    allow-authentication=false
    primary-color=#054f16
>
</rapi-doc>
</div>
<%def name="title()">API - newTrackon</%def>
