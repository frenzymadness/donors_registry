/**
 * Sets up highlighting of values overriden in donors_override
 * @param {string} url The URL to request (url_for('donor.get_overrides'))
 * @param {object} columnDefs DataTables columnDefs
 * @param {Function} onDataReady Called when information about overrides is downloaded
 */
function highlightOverridenValues(url, columnDefs, onDataReady) {
    let overrides = {}; // Will be set by an AJAX request

    for (const column of ["first_name", "last_name", "address", "city", "postal_code", "kod_pojistovny"]) {
        columnDefs.push({
            "targets": column,
            "name": column,
            "render": function (data, type, row, meta) {
                // We only want to highlight the value that is displayed
                // to the user, not the ones used for searching and sorting
                if (type != "display") return data;
                
                let rodneCislo;
                if (row instanceof Array)
                    rodneCislo = row[0]
                else
                    rodneCislo = row.rodne_cislo;

                if (overrides.hasOwnProperty(rodneCislo) && overrides[rodneCislo][column]) {
                    return `<mark title="Tato hodnota byla ručně nastavena">${data}</mark>`;
                } else {
                    return data;
                }
            }
        });
    }

    // Request the list of overrides
    $.getJSON(url, function (data) {
        overrides = data;
        onDataReady && onDataReady();
    });
}