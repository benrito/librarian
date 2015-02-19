!function (window, $) {
  var dashHeaders = $('.dash-section h2');
  var dashCollapsibles = $('.dash-collapsible');

  dashHeaders.on('click', expandCollapse);
  _.each(dashHeaders, addIcon);

  function expandCollapse(e) {
    e.preventDefault();
    dashCollapsibles.addClass('dash-collapsed');
    $(e.target).parent('.dash-collapsible').removeClass('dash-collapsed');
  }

  function addIcon(hdr) {
    $(hdr).prepend(templates.collapseIcon);
  }
}(this, jQuery);
