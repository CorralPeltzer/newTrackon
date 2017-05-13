<!DOCTYPE html>
<html lang="en">

<head>
  <meta charset="utf-8">
  <title>${self.title()}</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link rel="apple-touch-icon" sizes="180x180" href="/apple-touch-icon.png">
  <link rel="icon" type="image/png" href="/favicon-32x32.png" sizes="32x32">
  <link rel="icon" type="image/png" href="/favicon-16x16.png" sizes="16x16">
  <link rel="manifest" href="/manifest.json">
  <link rel="mask-icon" href="/safari-pinned-tab.svg" color="#25802c">
  <meta name="theme-color" content="#ffffff">
  <link rel="stylesheet" href="/static/css/theme.min.css" />
  <link rel="stylesheet" href="/static/css/custom.min.css" />
  <link href="https://fonts.googleapis.com/css?family=Roboto" rel="stylesheet">
  <script src="https://cdnjs.cloudflare.com/ajax/libs/jquery/3.2.1/jquery.min.js"></script>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/twitter-bootstrap/3.3.7/js/bootstrap.min.js"></script>
</head>

<body>
  <div class="navbar navbar-default navbar-fixed-top">
    <div class="container">
      <div class="navbar-header">
        <a href="./" class="navbar-brand">newTrackon</a>
        <button class="navbar-toggle" type="button" data-toggle="collapse" data-target="#navbar-main">
          <span class="icon-bar"></span>
          <span class="icon-bar"></span>
          <span class="icon-bar"></span>
        </button>
      </div>
      <div class="navbar-collapse collapse" id="navbar-main">
        <ul class="nav navbar-nav">
          <li><a href="/">Home</a></li>
          <li><a href="/list">List</a></li>
          <li><a href="/submitted">Submitted</a></li>
          <li><a href="/faq">FAQ</a></li>
          <li><a href="/api">API</a></li>
          <li><a href="/raw">Raw data</a></li>
          <li><a href="https://github.com/CorralPeltzer/newTrackon">Source</a></li>
        </ul>
        <ul class="nav navbar-nav navbar-right">
          <li><a href="/about">about</a></li>
        </ul>
      </div>
    </div>
  </div>

  ${self.body()}


<footer class="footer">
      <p class="text-center">A <a href="https://twitter.com/CorralPeltzer">@CorralPeltzer</a> creation based on an <a href="http://uriel.cat-v.org/">Uriel</a> project</p>
  </div>
</footer>



</body>

</html>
<%def name="title()">newTrackon: Tracking the trackers</%def>
<%def name="extraheaders()">
</%def>
