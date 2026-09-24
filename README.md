# Grocery Scanner

## Goal

Create an inexpensive, simple, self-hostable system for managing groceries in which scanning a QR code or NFC tag adds to a common shopping list, instantiable on a per-household basis.

## Definitions

- Scannable: A QR code, NFC tag, or just some real-world object that can produce a URL for a smart phone.
- Router Page: A statically-hosted HTML page containing some javascript used to redirect users to other URLs.
- Main Inventory File: Abbreviated MIF. A markdown file containing groceries following a human-readable but machine-parsable format.
- Scanner User: A user with a smart phone (or other capable device) that can scan Scannables.
- Admin User: A user responsible for updating what URLs the Scannables will redirect to.
- NXPTagWriter: A third-party app that's used to write to NFC tags. Surprisingly free.

## Business Logic

- When a Scanner User scans a Scannable (likely with their smart phone), they SHOULD be able to confirm what item they're adding.
- An Admin User MUST be able to change what URLs Scannables redirect to without needing to physically modify the Scannables themselves (aside from one-time setup).
- An Admin User MUST be able to add new entries to the MIF with either a text editor or the same app that generates the Router Page.
- Respect the terms of service of whatever stores are involved within reason.

## Implementation Details

- All Scannables SHOULD store a link to a Router Page, but each have a single different "id" URL parameter.
- A Router Page SHOULD use javascript to extract the value of the id parameter, resolve the appropriate shopping link from that id, then redirect the user to that link. 
- The MIF file format SHOULD feature one item per line, preferably in a form that accepts comments or arbitrary data after a link. Currently using markdown formattable as a todo list, e.g.:
```
- [ ] [Apple Chips](https://www.amazon.com/Seneca-Cinnamon-Delicious-Orchards-Perfection/dp/B0977P8GNL/)
- [ ] [BBQ Sauce](https://www.heb.com/product-detail/sweet-baby-ray-s-sweet-teriyaki-sauce-marinade/1964758)
- [ ] [Cotton Candy Grapes](https://www.heb.com/product-detail/fresh-cotton-candy-grapes/1717829)
```
- Requests performed through the URLS in Scannables can only be GET requests or queries of some kind, so a Scannable URL SHOULD resolve to a page that allows multiple actions to be taken on an item.

## Q & A

> Who is this for?

Primarily myself as I try to more effectively manage my household inventory now that I'm looking for a job (Since Sep. 11). I'm aiming to make at least the scanner component simple enough for my grandparents to use.

> Why not just use official apps?

I don't like installing more situational clutter on my phone, let alone registering for an account that's gonna get even more spam, and I want to be able to assign whatever URLs I want for products. 

> Why not use an actual database for storage? Or deploying to the cloud and setting up DNS and a user registration system and...

Remember when users ran software on their own machines without worrying about creating some account on a site and adding their credit card data? I'm not here to entertain more complexity narcissism than needed.

> Will you add integration with `___`?

If it exposes a REST API that wants to play nice with end users without making me jump through a bunch of hoops like making a developer account and an HTTPS-secured server for Oauth flows, then... likely. That "likely" can become a yes with appropriate compensation.

> Why are you being so overly formal with specification for what's just a static .html generator with extra steps?

Gotta practice my System Design somehow.

> AI Disclosure?

No generative AI was used for this project. However I'm going to design this under the assumption that my Dad will use AI to modify it as needed.
