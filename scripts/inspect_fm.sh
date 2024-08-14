if [ $1 ] ;  then {
  cdf_path=$FM_STATIC_DIR'/data_backup/'$1
}
else {
   cdf=$(redis-cli -h $REDIS_HOST -p $REDIS_PORT GET current_data_folder)
   cdf_path=$FM_STATIC_DIR'/data_backup/'$cdf
}
fi

echo "data folder path: $cdf_path"

rq_perf_path=$cdf_path'/rq_perf.csv'
sys_perf_path=$cdf_path'/sys_perf.csv'

#echo "Format of rq_perf"
#head -1 $rq_perf_path | awk -F ',' '{ i = 1 } { while ( i <= NF ) { print i "." $i ; i++ }}'

#echo -e  "\nFormat of sys_perf"
#head -1 $sys_perf_path | awk -F ',' '{ i = 1 } { while ( i <= NF ) { print i "." $i ; i++ }}'

echo -e "\n Queue build ups"
awk -F ',' '{ if( substr($6,2,1) > 5 ) print $5 " had " substr($6,2,1) " jobs at " $1}' $rq_perf_path

