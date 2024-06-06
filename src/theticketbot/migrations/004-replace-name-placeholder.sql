UPDATE inbox SET default_ticket_name =
    replace(replace(default_ticket_name,
        '${name}', '${author}'),
        '$name', '$author'
    );
