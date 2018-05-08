(function(){
    $(".marker-container").each(function(index, element){
        var container = $(element);
        var markers = container.find(".marker");
        var nMarkers = markers.length;
        if (nMarkers) {
            var totalWidth = container.width();
            var focusedMinWidth = totalWidth / 2;
            var tabWidth = nMarkers > 1 ? Math.min(12, (totalWidth - focusedMinWidth) / (nMarkers - 1)) : 0;
            var focusedWidth = totalWidth - (nMarkers - 1) * tabWidth;
            var reOrder = function() {
                var marker = $(this);
                marker.css({zIndex: nMarkers - 1});
                marker.prevAll().each(function(index, e){
                    $(e).css({zIndex: nMarkers - index - 2});
                });
                marker.nextAll().each(function(index, e){
                    $(e).css({zIndex: nMarkers - index - 2});
                });
            };
            for (var i=0; i<nMarkers; i++) {
                var marker = $(markers[i]);
                marker.css({
                    left: i * tabWidth + "px",
                    width: focusedWidth + "px",
                    zIndex: i
                });
                marker.click(reOrder);
            }
        }
    });
})();