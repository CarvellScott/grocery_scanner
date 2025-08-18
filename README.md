# Grocery Scanner

This is a sort of work-in-progress self-hosted means of managing my groceries. The idea was to be able to scan a QR code to add whatever groceries I'm missing to my online grocery list. It's intended to be VERY minimal, with few external dependencies and self-hostable from a freshly-provisioned system. (Such as the terminal on my Pixel 9a which keeps crashing and making me reset it)

- The QR code portion kinda fell through because of how annoying it'd be to replace each one of them, so I'm going for NFC tags instead. I don't want to depend on some website that will make them expire so I'm using NXPTagWriter to write URLs directly to my tags
- Because you can only perform GET requests via QR codes and NFC tags, some best practices such as "GET requests should not alter the state of the system" are will need to be ignored. 
- My grocery store doesn't like playing nice with people trying to reverse engineer/manipulate their API either so I'm opting to just store the URL to the item page to buy it online.
- Documentation is fairly minimal because it's still in very early stages.

I'm kind of just focusing on making it exist first and making it good later.

## Q & A:

> Q: How many users does this have?
A: Three. Me, myself, and I.

> Q: Have you thought about using an actual database for storage?
A: Yes, but the self-hosted nature of the project means that simplicity takes priority. I've created an abstraction to work with grocery items that mimics something along the lines of a key-value store, so I might go with redis if I am to go for something where scaling is important. I'm also willing to consider sqlite3 given that Python3 has a dedicated module for it. At the moment however, I don't need anything more complex than a .csv file.

> Q: What javascript framework do you use?
A: [vanilla js](http://vanilla-js.com/). Though I've been tempted to use htmx.

> Q: Will you be adding LLM integration?
A: Short answer: no. Long answer: noooooooooo.

> Q: Where's the documentation?
A: It's in a future commit.
