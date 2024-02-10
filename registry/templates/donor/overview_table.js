function create_tooltip_for_donations(data) {
    var title = ``;
    Object.keys(data).forEach((slug, index) => {
        if (slug != "total")
            title += `${data[slug]["name"]}: ${data[slug]["count"]}\n`;
    });
    return `<span data-toggle="modal" data-target="#titleModal" title="${title}">❓</span>`;
}

var dataTable = null;

$(document).ready( function () {
    const columnDefs = [
        {
            "targets": "rodne_cislo",
            "render": function (data, type, row, meta) {
                if (type == "display")
                    return "<a href='"+"{{ url_for('donor.detail', rc='REPLACE_ME') }}".replace("REPLACE_ME", row.rodne_cislo) + "'>" + row.rodne_cislo + "</a>"
                else
                    return data;
            }
        }, {
            "targets": "donations",
            "render": function (data, type, row, meta) {
                return data.total + create_tooltip_for_donations(data);
            }
        }, {
            "targets": "note",
            "render": function ( data, type, row, meta ) {
              if (data)
                return `<span data-toggle="modal" data-target="#titleModal" title="${data}">⚠️</span>`;
              return "";
            },
            "orderable": false,
        },
    ];

    highlightOverridenValues("{{ url_for('donor.get_overrides') }}", {{ override_column_names | safe }}, columnDefs, function() {
        if (dataTable !== null)
            dataTable.draw("page");
    });

    $.fn.dataTable.ext.order.intl('cs-CZ');

    dataTable = $('#overview').DataTable({
        language: {
            url: '//cdn.datatables.net/plug-ins/1.10.21/i18n/Czech.json'
        },
        "processing": true,
        "serverSide": true,
        "stateSave": true,
        "stateDuration": -1, // -1 means session storage in the current browser window
        "ajax": "{{ url_for('donor.overview_data') }}",
        "columns": [
            {% for column_class in column_names.keys() -%}
                {"data": "{{ column_class }}"},
            {%- endfor %}
        ],
        "columnDefs": columnDefs,
        "buttons": [{
            extend: 'excel',
            text: 'Stáhnout tabulku',
            title: '',
        }],
        "dom": "Blfrtip",
    });
} );
