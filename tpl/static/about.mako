<%inherit file="base.mako"/>
<div class=grid_12>

<h2 id="page-heading">About Trackon.org</h2>

<p>Trackon is a site dedicated to gather and display information about the status
and capabilities of open/public BitTorrent trackers.</p>


<h3>Contact</h3>

<p>For suggestions, bug reports, or any other feedback <a href="http://uriel.cat-v.org/contact">see my contact page</a> or join #bittorrent in irc.freenode.org or #suckless in irc.oftc.net.</p>


<h3>Thanks</h3>

<p>Thanks to everyone that has provided feedback and input about the project.

<p>Here is a list of some of the people that have helped make trackon possible:
<ul>
<li>Medecau in #bittorrent for ideas, feedback and beta-testing.
<li>Moraes and nickjohnson in #appengine for excellent technical help while dealing with App Engine.
<li>The authors of the sorttable JS script
<li>Stephen Bau for creating fluid960gs, which seems to be the only decent CSS 'framework' that can actually scale up and down gracefully to arbitrary font sizes.
<li>Grozdan, for reporting errors and adding many trackers.
</ul>

<div class="center">
<img style="border: solid black 0.4em" src='http://upload.wikimedia.org/wikipedia/commons/3/3e/Nine-Dragons1.jpg' title='Trago is the mascot dragon of Trackon.org' alt='Trago the dragon' />
</div>

</div>

<%def name="title()">About Trackon.org</%def>
