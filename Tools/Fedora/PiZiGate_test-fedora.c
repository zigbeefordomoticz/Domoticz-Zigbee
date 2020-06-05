#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include <unistd.h>			//Used for UART
#include <fcntl.h>			//Used for UART
#include <termios.h>		//Used for UART

#ifndef COULEURS
#define COULEURS
 
#include <stdlib.h>
#include <stdio.h>
 
#define clrscr() printf("\033[H\033[2J")
#define color(param) printf("\033[%sm",param)
/*Paramètre  Couleur
30 Noir |31 Rouge | 32 Vert | 33 Jaune | 34 Bleu| 35 Magenta | 36 Cyan | 37 Blanc*/
#endif

const float VERSION=1.2;
char *revisionTabs[] ={"9000c1","a02082","a020a0","a020d3","a22082","a220a0","a32082","a52082","a22083","a02100"};

char serialPort[50];
char command[100];


typedef int (*cmpfunc)(void *, void *);

int in_array(void *array[], int size, void *lookfor, cmpfunc cmp)
{
    int i;

    for (i = 0; i < size; i++)
        if (cmp(lookfor, array[i]) == 0)
            return 1;
    return 0;
}

char *trim (char *str)
{
      char *ibuf, *obuf;
 
      if (str)
      {
            for (ibuf = obuf = str; *ibuf; )
            {
                  while (*ibuf && (isspace (*ibuf)))
                        ibuf++;
                  if (*ibuf && (obuf != str))
                        *(obuf++) = ' ';
                  while (*ibuf && (!isspace (*ibuf)))
                        *(obuf++) = *(ibuf++);
            }
            *obuf = '\0';
      }
      return (str);
}

int set_interface_attribs(int fd, int speed)
{
    struct termios tty;

    if (tcgetattr(fd, &tty) < 0) {
		color("31;1");
        printf("- Error from tcgetattr: %s\n", strerror(errno));
		color("0");
        return -1;
    }

    cfsetospeed(&tty, (speed_t)speed);
    cfsetispeed(&tty, (speed_t)speed);

    tty.c_cflag |= (CLOCAL | CREAD);    /* ignore modem controls */
    tty.c_cflag &= ~CSIZE;
    tty.c_cflag |= CS8;         /* 8-bit characters */
    tty.c_cflag &= ~PARENB;     /* no parity bit */
    tty.c_cflag &= ~CSTOPB;     /* only need 1 stop bit */
    tty.c_cflag &= ~CRTSCTS;    /* no hardware flowcontrol */

    /* setup for non-canonical mode */
    tty.c_iflag &= ~(IGNBRK | BRKINT | PARMRK | ISTRIP | INLCR | IGNCR | ICRNL | IXON);
    tty.c_lflag &= ~(ECHO | ECHONL | ICANON | ISIG | IEXTEN);
    tty.c_oflag &= ~OPOST;

    /* fetch bytes as they become available */
    tty.c_cc[VMIN] = 1;
    tty.c_cc[VTIME] = 1;

    if (tcsetattr(fd, TCSANOW, &tty) != 0) {
		color("31;1");
        printf("- Error from tcsetattr: %s\n", strerror(errno));
		color("0");
        return -1;
    }
    return 0;
}

void set_mincount(int fd, int mcount)
{
    struct termios tty;

    if (tcgetattr(fd, &tty) < 0) {
		color("31;1");
        printf("- Error tcgetattr: %s\n", strerror(errno));
		color("0");
        return;
    }

    tty.c_cc[VMIN] = mcount ? 1 : 0;
    tty.c_cc[VTIME] = 5;        /* half second timer */

    if (tcsetattr(fd, TCSANOW, &tty) < 0)
		color("31;1");
        printf("- Error tcsetattr: %s\n", strerror(errno));
		color("0"); 
}

int main(int argc, char ** argv) {
	int verifFiles=0;
	
	if (argc == 2)
    {
		sprintf(serialPort,"%s",argv[1]);
    }else{
		
		printf("\nVersion : %0.1f \n",VERSION);
		printf("Usage : ./PiZiGate_test <Serial port> \n\n");
		exit(0);
		
	}
	
	int fd_uart = -1;
	
	printf("Opening : %s ...\n",serialPort);
	
	fd_uart = open(serialPort, O_RDWR | O_NOCTTY | O_NDELAY);		//Open in non blocking read/write mode
	if (fd_uart < 0)
	{
		//ERROR - CAN'T OPEN SERIAL PORT
		color("31;1");
		printf("- Error - Unable to open UART.  Ensure it is not in use by another application\n");
		color("0");
		exit(0);
	}
	color("32;1");
	printf("+ %s opened --> OK\n",serialPort);
	color("0");
	
	set_interface_attribs(fd_uart, B115200);
	usleep (100000);
	int wlen;
	char data[11];
	sprintf(data,"%c%c%c%c%c%c%c%c%c%c\n",0x01,0x02,0x10,0x10,0x02,0x10,0x02,0x10,0x10,0x03);
	color("32;1");
	printf("+ Packet 01 02 10 10 02 10 02 10 10 03 sent --> OK\n");
	color("0");
	wlen = write(fd_uart,data,strlen(data));
    if (wlen <0 ) {
		color("31;1");
        printf("- Error from write: %d, %d\n", wlen, errno);
		color("0");
    }
    tcdrain(fd_uart);    /* delay for output */
	
	unsigned char buf[512];
    int rdlen;
	usleep (250000); 
	
	rdlen = read(fd_uart, buf, sizeof(buf) - 1);
	if (rdlen > 0) {
		
		color("32;1");
		printf("+ Packet received --> OK\n");
		color("0");
		int i,translate;
		int j=0;
		char tmpBuff[512];
		color("36;1");
		printf("size : %d\n ",rdlen);
		for (i=0; i<rdlen;i++)
		{
			
			if (buf[i]==2)
			{
				translate=1;
				
				char tmp=0;
				i++;
				tmp=buf[i];
				tmp^=0x10;
			
				//tmpBuff[j]=buf[i];
				//tmpBuff[j]^=0x10;
				printf("%02x ",tmp);
				
				//j++;
			}else if (buf[i]==3)
			{
				//tmpBuff[j]="\n";
				printf("%02x \n",buf[i]);
				//j++;
			}else{
				translate=0;
				printf("%02x ",buf[i]);
				//tmpBuff[j]=buf[i];
				//j++;
			}
			
		}
		printf("\n");
		//tmpBuff[j]='\0';
		
	
		//printf("Release : %02x%02x\n",tmpBuff[0],tmpBuff[1]);
		//printf("Version : %02x%02x\n",tmpBuff[2],tmpBuff[3]);
		color("0");
		exit(0);
	}else{
		color("31;1");
		printf("- No packet received - size sent : %d - error : %d\n", wlen, errno);
		color("0");
	}
	
	close(fd_uart);
	
}
