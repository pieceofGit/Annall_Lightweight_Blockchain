The blockchain database is created once for each writer.
When a client sends a payload to a writer, its message is saved into the payload field.
Things are only written into the database when the round's winning writer has an item on its payload queue to write.
