__export_mysql() {

echo "Export data to backup."

mysqldump  -u$MYSQL_USER -p $MYSQL_DATABASE --no-tablespaces > ../scripts/data_backup.sql

echo "Finished exporting the app data to backup."

}

# Call all functions
__export_mysql