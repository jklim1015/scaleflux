#!/bin/bash

#Clearing the prom file
echo "" > /usr/local/bin/node_exporter_textfile_collector/custom_metrics.prom
first_check=true

#Looping through each namespace
for nvme in /sys/class/nvme/nvme0/nvme*; do
   np=$(basename $nvme)

   #Setting smartlog path
   smartlog0xc2=`nvme get-log "/dev/$np" --log-id=0xc2 --log-len=128 2>/dev/null`

   #Run the command and extract the targeted information
   nuse=$(sudo nvme id-ns "/dev/$np" -H | awk '/nuse/{print $3}')
   nsze=$(sudo nvme id-ns "/dev/$np" -H | awk '/nsze/{print $3}')
   ncap=$(sudo nvme id-ns "/dev/$np" -H | awk '/ncap/{print $3}')
   tnvmcap=$(sudo nvme id-ctrl /dev/nvme0 | awk '/tnvmcap/{print $3}' | tr -d ',')

   fps=`echo "$smartlog0xc2" | sed -n 8p | cut -c 31-54 | sed 's/ //g'`
   comp_ratio=`echo "$smartlog0xc2" | sed -n 9p | cut -c 19-30 | sed 's/ //g'`

   #Grabbing data/byte size
   output=$(sudo nvme id-ns "/dev/$np" -H | grep "(in use)")
   bytes=$(echo "$output" | awk -F "Data Size: " '{print $2}' | awk '{print $1}')

   #Checking for filesystem and extracting targeted informatiom
   if sudo mount | grep $np; then
      used=$(sudo df "/dev/$np" --output=used,avail | awk 'NR==2 {print $1}')
      avail=$(sudo df "/dev/$np" --output=used,avail | awk 'NR==2 {print $2}')
      used_converted=$(echo "scale=2; $used / (1000*1000)" | bc)
      avail_converted=$(echo "scale=2; $avail / (1000*1000)" | bc)
   else
      used_converted=0
      avail_converted=0
   fi

   #Convert to GB
   to_GB() {
       local value=$(printf "%d" $1)
       local result=$(echo "scale=2; ($value * $bytes) / (1000^3)" | bc)
       echo $result
   }

   stringSwitch8B() {
       output=$1
       j=14
       string=""
       for ((z = 1; z <= 8; z++)); do
           string=$string${output:$j:2}
           j=$j-2
       done
       let string=16#$string
       return $string
   }

   stringSwitch() {
       output=$1
       j=6
       string=""
       for ((z = 1; z <= 4; z++)); do
           string=$string${output:$j:2}
           j=$j-2
       done
       let string=16#$string
       return $string
   }

   #Converting information to GB
   nuse_converted=$(to_GB $nuse)
   nsze_converted=$(to_GB $nsze)
   ncap_converted=$(to_GB $ncap)

   stringSwitch8B $fps
   count=$string
   fps_converted=$(((count-97696368)/1953504+50))

   stringSwitch $comp_ratio
   comp_converted=$((10#$string))

   disk_cap=$(echo "($used_converted + $avail_converted)" | bc)
   tnvmcap_converted=$(echo "scale=2; $tnvmcap / (1000^3)" | bc)

   #Output the information to the prom file
   if $first_check; then
      echo -e "# HELP nuse The description of the nuse metric\n# TYPE nuse gauge" >> /usr/local/bin/node_exporter_textfile_collector/custom_metrics.prom
      echo "nuse{device=\"$np\"} $nuse_converted" >> /usr/local/bin/node_exporter_textfile_collector/custom_metrics.prom

      echo -e "# HELP nsze The description of the nsze metric\n# TYPE nsze gauge" >> /usr/local/bin/node_exporter_textfile_collector/custom_metrics.prom
      echo "nsze{device=\"$np\"} $nsze_converted" >> /usr/local/bin/node_exporter_textfile_collector/custom_metrics.prom

      echo -e "# HELP ncap The description of the ncap metric\n# TYPE ncap gauge" >> /usr/local/bin/node_exporter_textfile_collector/custom_metrics.prom
      echo "ncap{device=\"$np\"} $ncap_converted" >> /usr/local/bin/node_exporter_textfile_collector/custom_metrics.prom

      echo -e "# HELP fps The description of the fps metric\n# TYPE fps gauge" >> /usr/local/bin/node_exporter_textfile_collector/custom_metrics.prom
      echo "fps{device=\"$np\"} $fps_converted" >> /usr/local/bin/node_exporter_textfile_collector/custom_metrics.prom

      echo -e "# HELP compratio The description of the compratio metric\n# TYPE compratio gauge" >> /usr/local/bin/node_exporter_textfile_collector/custom_metrics.prom
      echo "compratio{device=\"$np\"} $comp_converted" >> /usr/local/bin/node_exporter_textfile_collector/custom_metrics.prom

      echo -e "# HELP du The description of the du metric\n# TYPE du gauge" >> /usr/local/bin/node_exporter_textfile_collector/custom_metrics.prom
      echo "du{device=\"$np\"} $used_converted" >> /usr/local/bin/node_exporter_textfile_collector/custom_metrics.prom

      echo -e "# HELP df The description of the df metric\n# TYPE df gauge" >> /usr/local/bin/node_exporter_textfile_collector/custom_metrics.prom
      echo "df{device=\"$np\"} $avail_converted" >> /usr/local/bin/node_exporter_textfile_collector/custom_metrics.prom

      echo -e "# HELP disk_cap The description of the df metric\n# TYPE disk_cap gauge" >> /usr/local/bin/node_exporter_textfile_collector/custom_metrics.prom
      echo "disk_cap{device=\"$np\"} $disk_cap" >> /usr/local/bin/node_exporter_textfile_collector/custom_metrics.prom

      echo -e "# HELP tnvmcap The description of the df metric\n# TYPE tnvmcap gauge" >> /usr/local/bin/node_exporter_textfile_collector/custom_metrics.prom
      echo "tnvmcap{device=\"$np\"} $tnvmcap_converted" >> /usr/local/bin/node_exporter_textfile_collector/custom_metrics.prom

   else
      echo "nuse{device=\"$np\"} $nuse_converted" >> /usr/local/bin/node_exporter_textfile_collector/custom_metrics.prom

      echo "nsze{device=\"$np\"} $nsze_converted" >> /usr/local/bin/node_exporter_textfile_collector/custom_metrics.prom

      echo "ncap{device=\"$np\"} $ncap_converted" >> /usr/local/bin/node_exporter_textfile_collector/custom_metrics.prom

      echo "fps{device=\"$np\"} $fps_converted" >> /usr/local/bin/node_exporter_textfile_collector/custom_metrics.prom

      echo "compratio{device=\"$np\"} $comp_converted" >> /usr/local/bin/node_exporter_textfile_collector/custom_metrics.prom

      echo "du{device=\"$np\"} $used_converted" >> /usr/local/bin/node_exporter_textfile_collector/custom_metrics.prom

      echo "df{device=\"$np\"} $avail_converted" >> /usr/local/bin/node_exporter_textfile_collector/custom_metrics.prom

      echo "disk_cap{device=\"$np\"} $disk_cap" >> /usr/local/bin/node_exporter_textfile_collector/custom_metrics.prom

      echo "tnvmcap{device=\"$np\"} $tnvmcap_converted" >> /usr/local/bin/node_exporter_textfile_collector/custom_metrics.prom
   fi
   first_check=false
done
