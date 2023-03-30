__import_mysql() {
echo "Running the start_mysql function."
echo "Import the app data from backup."
mysql -u$MYSQL_USER -p$ $MYSQL_DATABASE < /scripts/$MYSQL_DATABASE_CREATE_SQL
echo "Finished importing the app data from backup."


}

# Call all functions
__import_mysql