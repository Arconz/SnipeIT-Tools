# SnipeIT-Tools
A set of tools I have created to help me work with SnipeIT

transfer will take all accessories a user has assigned to them and assign them to another user.
snipeit_inv_sign Creates a digitally signable PDF for (a) user(s). 
It will first ask for a user name, email, or user ID if none is entered it will default to all users. 
The pdf is created in two steps. 
First it uses tables to layout text, assets, and accessories. 
(The text can be changed in the config.ini or directly written in by removing variables)
Then it logs where the signature field is amended using pyhanko.
