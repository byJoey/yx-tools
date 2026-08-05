package app

import (
	"bytes"
	"fmt"
	"os"
	"os/exec"
	"runtime"
	"strings"
	"sync"
)

// cronTag 用于识别本程序写入的任务行，便于列出与清理
const cronTag = "# yx-tools"

// CronJob 是一条已登记的定时任务
type CronJob struct {
	Schedule string
	Command  string
	Raw      string
}

// CronSupported 报告当前系统是否支持 crontab 方式。
// 光看命令在不在不够：容器里 crontab 常常装着却不可用
// （非 root 且二进制没有 suid 位，报 "must be suid to work properly"），
// 所以实际跑一次 crontab -l 来判断。
func CronSupported() bool {
	if runtime.GOOS == "windows" {
		return false
	}
	cronOnce.Do(func() {
		if _, err := exec.LookPath("crontab"); err != nil {
			return
		}
		cmd := exec.Command("crontab", "-l")
		var stderr bytes.Buffer
		cmd.Stderr = &stderr
		err := cmd.Run()
		if err == nil {
			cronOK = true
			return
		}
		// 没有任务时退出码非零属正常，只有明确的不可用信息才判定为不支持
		msg := strings.ToLower(stderr.String())
		cronOK = !strings.Contains(msg, "suid") &&
			!strings.Contains(msg, "permission denied") &&
			!strings.Contains(msg, "not allowed")
	})
	return cronOK
}

var (
	cronOnce sync.Once
	cronOK   bool
)

func readCrontab() ([]string, error) {
	out, err := exec.Command("crontab", "-l").Output()
	if err != nil {
		// 没有任何任务时 crontab -l 会返回非零，视为空表
		if ee, ok := err.(*exec.ExitError); ok && len(ee.Stderr) > 0 &&
			strings.Contains(strings.ToLower(string(ee.Stderr)), "no crontab") {
			return nil, nil
		}
		if len(out) == 0 {
			return nil, nil
		}
	}
	lines := strings.Split(strings.TrimRight(string(out), "\n"), "\n")
	if len(lines) == 1 && lines[0] == "" {
		return nil, nil
	}
	return lines, nil
}

func writeCrontab(lines []string) error {
	body := strings.Join(lines, "\n")
	if body != "" && !strings.HasSuffix(body, "\n") {
		body += "\n"
	}
	cmd := exec.Command("crontab", "-")
	cmd.Stdin = bytes.NewBufferString(body)
	var stderr bytes.Buffer
	cmd.Stderr = &stderr
	if err := cmd.Run(); err != nil {
		return fmt.Errorf("写入 crontab 失败: %v %s", err, strings.TrimSpace(stderr.String()))
	}
	return nil
}

// ListCronJobs 列出本程序登记的定时任务
func ListCronJobs() ([]CronJob, error) {
	if !CronSupported() {
		return nil, fmt.Errorf("当前系统不支持 crontab")
	}
	lines, err := readCrontab()
	if err != nil {
		return nil, err
	}
	var jobs []CronJob
	for _, ln := range lines {
		if !strings.Contains(ln, cronTag) || strings.HasPrefix(strings.TrimSpace(ln), "#") {
			continue
		}
		body := strings.TrimSpace(strings.Split(ln, cronTag)[0])
		fields := strings.Fields(body)
		if len(fields) < 6 {
			continue
		}
		jobs = append(jobs, CronJob{
			Schedule: strings.Join(fields[:5], " "),
			Command:  strings.Join(fields[5:], " "),
			Raw:      ln,
		})
	}
	return jobs, nil
}

// AddCronJob 追加一条定时任务；replace 为真时先清掉本程序已有的任务
func AddCronJob(schedule, command string, replace bool) error {
	if !CronSupported() {
		return fmt.Errorf("当前系统不支持 crontab，请手动配置计划任务")
	}
	if len(strings.Fields(schedule)) != 5 {
		return fmt.Errorf("时间表达式需要 5 段，如 \"0 */6 * * *\"")
	}
	lines, err := readCrontab()
	if err != nil {
		return err
	}
	if replace {
		kept := lines[:0]
		for _, ln := range lines {
			if !strings.Contains(ln, cronTag) {
				kept = append(kept, ln)
			}
		}
		lines = kept
	}
	lines = append(lines, fmt.Sprintf("%s %s %s", schedule, command, cronTag))
	return writeCrontab(lines)
}

// RemoveCronJobs 清掉本程序登记的全部定时任务，返回删除条数
func RemoveCronJobs() (int, error) {
	if !CronSupported() {
		return 0, fmt.Errorf("当前系统不支持 crontab")
	}
	lines, err := readCrontab()
	if err != nil {
		return 0, err
	}
	kept := make([]string, 0, len(lines))
	n := 0
	for _, ln := range lines {
		if strings.Contains(ln, cronTag) {
			n++
			continue
		}
		kept = append(kept, ln)
	}
	if n == 0 {
		return 0, nil
	}
	return n, writeCrontab(kept)
}

// SelfPath 返回可执行文件的绝对路径，供定时任务使用
func SelfPath() string {
	exe, err := os.Executable()
	if err != nil {
		return "yx"
	}
	return exe
}
