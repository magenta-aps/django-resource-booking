$(function() {
    window.formset = {
        _replaceCounter: function(string, newIndex){
            return string.replace(/-(\d)-/, function(match, group, index, full) {
                return "-" + (newIndex) + "-";
            });
        },
        addRow: function(totalRowsEl, maxRowsEl, rowPrototype, container) {
            totalRowsEl = $(totalRowsEl);
            maxRowsEl = $(maxRowsEl);
            var totalRows = parseInt(totalRowsEl.val(), 10);
            var maxRows = parseInt(maxRowsEl.val(), 10);

            if (totalRows < maxRows) {
                var newRow = $(rowPrototype).clone();
                newRow.attr("id", "");
                newRow.find("input,select").each(function(){
                    this.id = formset._replaceCounter(this.id, totalRows);
                    this.name = formset._replaceCounter(this.name, totalRows);
                    if (this.type == "checkbox") {
                        this.checked = null;
                    } else {
                        this.value = "";
                    }
                });
                newRow.find("label").each(function(){
                    this.htmlFor = formset._replaceCounter(this.htmlFor, totalRows);
                });
                $(container).append(newRow);
                totalRowsEl.val(totalRows + 1);
                return newRow;
            }
        },
        removeRow: function(totalRowsEl, row) {
            totalRowsEl = $(totalRowsEl);
            $(row).remove();
            totalRowsEl.val(parseInt(totalRowsEl.val(), 10) - 1);
        }
    };

});

