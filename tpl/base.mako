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
  <link rel="stylesheet" href="https://fonts.googleapis.com/css?family=Roboto" />
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/4.7.0/css/font-awesome.min.css" integrity="sha256-eZrrJcwDc/3uDhsdt61sL2oOBY362qM3lon1gyExkL0=" crossorigin="anonymous" />
  <script src="https://cdnjs.cloudflare.com/ajax/libs/jquery/3.2.1/jquery.min.js" integrity="sha256-hwg4gsxgFZhOsEEamdOYGBf13FyQuiTwlAQgxVSNgt4=" crossorigin="anonymous"></script>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/twitter-bootstrap/3.3.7/js/bootstrap.min.js" integrity="sha256-U5ZEeKfGNOja007MMD3YBI0A3OSZOQbeG6z2f2Y0hu8=" crossorigin="anonymous"></script>
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
          % if active == 'main':
          <li class="active"><a href="/"><i class="fa fa-home" aria-hidden="true"></i> Home</a></li>
          % else:
          <li><a href="/"><i class="fa fa-home" aria-hidden="true"></i> Home</a></li>
          % endif
          % if active == 'list':
          <li class="active"><a href="/list"><i class="fa fa-list" aria-hidden="true"></i> List</a></li>
          % else:
          <li><a href="/list"><i class="fa fa-list" aria-hidden="true"></i> List</a></li>
          % endif
          % if active == 'submitted':
          <li class="active"><a href="/submitted"><i class="fa fa-plus" aria-hidden="true"></i> Submitted</a></li>
          % else:
          <li><a href="/submitted"><i class="fa fa-plus" aria-hidden="true"></i> Submitted</a></li>
          % endif
          % if active == 'faq':
          <li class="active"><a href="/faq"><i class="fa fa-question-circle" aria-hidden="true"></i> FAQ</a></li>
          % else:
          <li><a href="/faq"><i class="fa fa-question-circle" aria-hidden="true"></i> FAQ</a></li>
          % endif
          % if active == 'api':
          <li class="active"><a href="/api"><i class="fa fa-code" aria-hidden="true"></i> API</a></li>
          % else:
          <li><a href="/api"><i class="fa fa-code" aria-hidden="true"></i> API</a></li>
          % endif
          % if active == 'raw':
          <li class="active"><a href="/raw"><i class="fa fa-terminal" aria-hidden="true"></i> Raw data</a></li>
          % else:
          <li><a href="/raw"><i class="fa fa-terminal" aria-hidden="true"></i> Raw data</a></li>
          % endif
          <li><a href="https://github.com/CorralPeltzer/newTrackon"><i class="fa fa-github" aria-hidden="true"></i> Source</a></li>
        </ul>
        <ul class="nav navbar-nav navbar-right">
          % if active == 'about':
          <li class="active"><a href="/about"><i class="fa fa-user" aria-hidden="true"></i> About</a></li>
          % else:
          <li><a href="/about"><i class="fa fa-user" aria-hidden="true"></i> About</a></li>
          % endif
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
