$(function(){

    $(".paginated-list").each(function(){
        var $this = $(this);
        var items = $this.find($this.attr("data-list-item"));
        var pageSize = $this.attr("data-list-size") || 10;
        if (items.length >= pageSize) {
            var paginator = $this.find("ul.pagination");

            var page = 0;
            var lastPage = Math.ceil(items.length / pageSize) - 1;

            var showPage = function (p) {
                var beginIndex = p * pageSize;
                display = items.slice(beginIndex, beginIndex + pageSize);
                display.show();
                items.not(display).hide();
                page = p;
                updateButtons();
            };

            var prevButton = paginator.find(".prevbutton");
            prevButton.click(function(event) {
                if (page > 0) {
                    showPage(page - 1);
                }
                event.preventDefault();
                return false;
            });

            var nextButton = paginator.find(".nextbutton");
            nextButton.click(function (event) {
                if (page < lastPage) {
                    showPage(page + 1);
                }
                event.preventDefault();
                return false;
            });

            var pageButtonPrototype = paginator.find("li.pagebutton");
            var pageButtons = [];
            for (i=0; i<=lastPage; i++) {
                var pageButton = pageButtonPrototype.clone().text(i+1);
                pageButtons.push(pageButton);
            }
            pageButtonPrototype.after(pageButtons);
            pageButtonPrototype.remove();

            var updateButton = function(button, enabled) {
                button.toggleClass("disabled", !enabled);
            };

            var updateButtons = function() {
                updateButton(prevButton, page > 0);
                updateButton(nextButton, page < lastPage);
                for (var i=0; i<pageButtons.length; i++) {
                    var pageButton = pageButtons[i];
                    pageButton.empty();
                    var content;
                    if (page == i) {
                        pageButton.addClass("active");
                        content = $("<span>").html((i+1)+' <span class="sr-only">(aktiv side)</span>');
                    } else {
                        pageButton.removeClass("active");
                        content = $("<a>").text(i+1).click(function(p){
                            if (page !== p) {
                                showPage(p);
                            }
                        }.bind(null, i));
                    }
                    pageButton.append(content);
                }
            };

            showPage(0);
        }

    });
});